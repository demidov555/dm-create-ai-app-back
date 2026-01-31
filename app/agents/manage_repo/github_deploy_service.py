import io
import re
import time
import zipfile
from dataclasses import dataclass
from typing import Optional, Any

import requests


@dataclass
class WorkflowResult:
    ok: bool
    conclusion: str
    run_id: Optional[int] = None
    run_url: Optional[str] = None
    workflow_name: Optional[str] = None
    error_text: Optional[str] = None
    logs_text: Optional[str] = None


class GitHubDeployService:
    def __init__(
        self,
        token: str,
        owner: str | None,
        repo: str | None,
        api_base: str = "https://api.github.com",
    ):
        self.owner = owner
        self.repo = repo
        self.api_base = api_base.rstrip("/")

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "GitHubDeployService",
            }
        )

    def wait_build_and_get_error_text(
        self,
        head_sha: str,
        timeout_sec: int = 900,
        poll_sec: int = 5,
        per_page: int = 50,
        max_log_chars: int = 200_000,
        include_raw_logs: bool = False,
        event: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ) -> WorkflowResult:
        deadline = time.time() + timeout_sec

        run = self._wait_run_appears_by_sha(
            head_sha=head_sha,
            deadline=deadline,
            poll_sec=poll_sec,
            per_page=per_page,
            event=event,
            workflow_name=workflow_name,
        )
        if run is None:
            return WorkflowResult(
                ok=False,
                conclusion="timeout",
                error_text=f"Не найден workflow run для sha={head_sha} за {timeout_sec}s",
            )

        run_id = int(run["id"])
        run_url = run.get("html_url")
        wf_name = run.get("name")

        # ждём завершения run
        while time.time() < deadline:
            data = self._get_json(
                f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}")
            status = (data.get("status") or "").lower()
            conclusion = (data.get("conclusion") or "").lower()

            if status == "completed":
                if conclusion == "success":
                    return WorkflowResult(
                        ok=True,
                        conclusion="success",
                        run_id=run_id,
                        run_url=run_url,
                        workflow_name=wf_name,
                    )

                # не success -> тянем logs.zip (endpoint отдаёт redirect; requests его нормально фолловит) :contentReference[oaicite:2]{index=2}
                try:
                    zip_bytes = self._get_bytes(
                        f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs",
                        timeout=60,
                    )
                    files = self._unzip_logs(
                        zip_bytes, max_total_chars=max_log_chars)
                    err = self._extract_error_snippet(files)
                    raw = self._join_files(files) if include_raw_logs else None
                except Exception as e:
                    err = f"Не удалось скачать/распаковать logs.zip: {type(e).__name__}: {e}"
                    raw = None

                return WorkflowResult(
                    ok=False,
                    conclusion=conclusion or "unknown",
                    run_id=run_id,
                    run_url=run_url,
                    workflow_name=wf_name,
                    error_text=err,
                    logs_text=raw,
                )

            time.sleep(poll_sec)

        return WorkflowResult(
            ok=False,
            conclusion="timeout",
            run_id=run_id,
            run_url=run_url,
            workflow_name=wf_name,
            error_text=f"Workflow run {run_id} не завершился за {timeout_sec}s",
        )

    # ---------------- internals ----------------

    def _wait_run_appears_by_sha(
        self,
        head_sha: str,
        deadline: float,
        poll_sec: int,
        per_page: int,
        event: Optional[str],
        workflow_name: Optional[str],
    ) -> Optional[dict[str, Any]]:
        params: dict[str, Any] = {"head_sha": head_sha,
                                  "per_page": min(max(per_page, 1), 100)}
        if event:
            params["event"] = event

        while time.time() < deadline:
            try:
                data = self._get_json(
                    f"/repos/{self.owner}/{self.repo}/actions/runs",
                    params=params,
                )
                runs = data.get("workflow_runs") or []
            except Exception:
                time.sleep(poll_sec)
                continue

            if workflow_name:
                wn = workflow_name.lower()
                runs = [
                    r for r in runs
                    if (r.get("name") or "").lower() == wn
                    or wn in (r.get("name") or "").lower()
                ]

            if runs:
                def ts(r: dict[str, Any]) -> str:
                    # ISO-строки сравниваются лексикографически корректно для "свежее/старее"
                    return (r.get("run_started_at") or r.get("created_at") or "")

                active = [r for r in runs if (
                    r.get("status") or "").lower() != "completed"]
                if active:
                    return max(active, key=ts)
                return max(runs, key=ts)

            time.sleep(poll_sec)

        return None

    def _get_json(self, path: str, params: Optional[dict] = None, timeout: int = 20) -> dict:
        url = f"{self.api_base}{path}"
        r = self._session.get(url, params=params, timeout=timeout)
        if not r.ok:
            raise RuntimeError(
                f"GitHub API {r.status_code}: {self._safe_text(r)}")
        return r.json()

    def _get_bytes(self, path: str, params: Optional[dict] = None, timeout: int = 20) -> bytes:
        url = f"{self.api_base}{path}"
        r = self._session.get(url, params=params,
                              timeout=timeout, allow_redirects=True)
        if not r.ok:
            raise RuntimeError(
                f"GitHub API {r.status_code}: {self._safe_text(r)}")
        return r.content

    @staticmethod
    def _safe_text(resp: requests.Response, limit: int = 2000) -> str:
        try:
            return (resp.text or "")[:limit]
        except Exception:
            return "<no response text>"

    @staticmethod
    def _unzip_logs(zip_bytes: bytes, max_total_chars: int) -> list[tuple[str, str]]:
        """
        Возвращает список (filename, text). Обрезает суммарно до max_total_chars.
        """
        out: list[tuple[str, str]] = []
        total = 0
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in sorted(z.namelist()):
                if not (name.endswith(".txt") or name.endswith(".log")):
                    continue
                try:
                    text = z.read(name).decode("utf-8", errors="replace")
                except Exception:
                    continue

                if total >= max_total_chars:
                    break

                remain = max_total_chars - total
                if len(text) > remain:
                    text = text[:remain]
                out.append((name, text))
                total += len(text)
        return out

    @staticmethod
    def _join_files(files: list[tuple[str, str]]) -> str:
        return "\n".join([f"\n===== {n} =====\n{t}" for n, t in files]).strip()

    @staticmethod
    def _extract_error_snippet(files: list[tuple[str, str]], ctx_before: int = 50, ctx_after: int = 50) -> str:
        """
        Пытаемся найти наиболее “ошибочный” кусок логов.
        Если не нашли — вернём хвост самого длинного файла.
        """
        # самые частые маркеры ошибок в CI
        rx = re.compile(
            r"(##\[error\]|traceback\b|exception\b|fatal\b|^\s*error\b|npm ERR!|yarn .*error|"
            r"gradle.*failed|failed\b|build\s+failed|compilation\s+failed|segmentation fault)",
            re.IGNORECASE,
        )

        best_score = -1
        best_snip = None

        for fname, text in files:
            lines = text.splitlines()
            hits = [i for i, line in enumerate(lines) if rx.search(line)]
            if not hits:
                continue

            i = hits[-1]  # берём последнюю ошибку в файле
            a = max(0, i - ctx_before)
            b = min(len(lines), i + ctx_after)
            snippet = "\n".join(lines[a:b]).strip()

            score = len(hits) * 1000 + (100 if "error" in fname.lower()
                                        else 0) + len(snippet) // 200
            if score > best_score:
                best_score = score
                best_snip = f"===== {fname} =====\n{snippet}"

        if best_snip:
            return best_snip

        # fallback: хвост самого длинного файла
        if not files:
            return "(Логи пустые или не содержат txt/log файлов)"

        fname, text = max(files, key=lambda x: len(x[1]))
        tail_lines = text.splitlines()[-120:]
        return f"===== {fname} (tail) =====\n" + "\n".join(tail_lines).strip()
