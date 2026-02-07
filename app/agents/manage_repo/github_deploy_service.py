# app/agents/manage_repo/github_deploy_service.py
from __future__ import annotations

import asyncio
import io
import re
import time
import zipfile
from dataclasses import dataclass
from typing import Optional, Any

import requests


# =========================
# Public result model
# =========================

@dataclass
class WorkflowResult:
    ok: bool
    conclusion: str
    run_id: Optional[int] = None
    run_url: Optional[str] = None
    workflow_name: Optional[str] = None
    error_text: Optional[str] = None
    logs_text: Optional[str] = None


# =========================
# Internal job model
# =========================

@dataclass(frozen=True)
class _BuildJob:
    project_id: str
    agent_name: str
    head_sha: str
    include_raw_logs: bool
    timeout_sec: int
    poll_sec: int
    per_page: int
    max_log_chars: int
    event: Optional[str]
    workflow_name: Optional[str]


# =========================
# Service
# =========================

class GitHubDeployService:
    """
    Простой и рабочий сервис:

    - Внешний код НЕ блокируется.
    - Ты вызываешь `await submit_build(...)` -> получаешь Future.
    - Дальше можешь `res = await future` в нужном месте.
    - Внутри сервиса работает один воркер, который ждёт GitHub Actions
      (ожидание идёт в отдельном thread через asyncio.to_thread).

    Важно:
      owner = user.login
      repo  = repo_name (НЕ full_name)
    """

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        api_base: str = "https://api.github.com",
    ):
        if not token:
            raise ValueError("token is required")
        if not owner:
            raise ValueError("owner is required (use user.login)")
        if not repo:
            raise ValueError("repo is required (use repo name)")

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

        # очередь работ и "ожидающие" futures по (project_id, sha)
        self._q: asyncio.Queue[_BuildJob] = asyncio.Queue()
        self._pending: dict[tuple[str, str], asyncio.Future[WorkflowResult]] = {}
        self._worker_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    # =========================
    # Public async API
    # =========================

    def start(self) -> None:
        """Запускаем воркер один раз."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def submit_build(
        self,
        project_id: str,
        agent_name: str,
        head_sha: str,
        *,
        include_raw_logs: bool = False,
        timeout_sec: int = 900,
        poll_sec: int = 120,
        per_page: int = 50,
        max_log_chars: int = 200_000,
        event: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ) -> asyncio.Future[WorkflowResult]:
        loop = asyncio.get_running_loop()

        if not head_sha:
            fut: asyncio.Future[WorkflowResult] = loop.create_future()
            fut.set_result(
                WorkflowResult(ok=False, conclusion="no_sha", error_text="empty head_sha")
            )
            return fut

        self.start()

        key = (project_id, head_sha)

        async with self._lock:
            fut = self._pending.get(key)
            if fut is None or fut.done():
                fut = loop.create_future()
                self._pending[key] = fut

                await self._q.put(
                    _BuildJob(
                        project_id=project_id,
                        agent_name=agent_name,
                        head_sha=head_sha,
                        include_raw_logs=include_raw_logs,
                        timeout_sec=timeout_sec,
                        poll_sec=poll_sec,
                        per_page=per_page,
                        max_log_chars=max_log_chars,
                        event=event,
                        workflow_name=workflow_name,
                    )
                )

            return fut

    # =========================
    # Worker loop
    # =========================

    async def _worker_loop(self) -> None:
        while True:
            job = await self._q.get()
            key = (job.project_id, job.head_sha)

            try:
                # блокирующую логику уводим в отдельный thread
                res = await asyncio.to_thread(
                    self._wait_build_and_get_error_text_blocking,
                    job.head_sha,
                    job.timeout_sec,
                    job.poll_sec,
                    job.per_page,
                    job.max_log_chars,
                    job.include_raw_logs,
                    job.event,
                    job.workflow_name,
                )
            except Exception as e:
                res = WorkflowResult(
                    ok=False,
                    conclusion="monitor_error",
                    error_text=f"{type(e).__name__}: {e}",
                )

            # проставляем результат в Future
            async with self._lock:
                fut = self._pending.get(key)
                if fut is not None and not fut.done():
                    fut.set_result(res)
                # чистим pending, чтобы не накапливать
                self._pending.pop(key, None)

            self._q.task_done()

    # =========================
    # Blocking core (thread)
    # =========================

    def _wait_build_and_get_error_text_blocking(
        self,
        head_sha: str,
        timeout_sec: int,
        poll_sec: int,
        per_page: int,
        max_log_chars: int,
        include_raw_logs: bool,
        event: Optional[str],
        workflow_name: Optional[str],
    ) -> WorkflowResult:
        """
        Блокирующая функция (внутри thread).
        Ждёт появления workflow run по sha и затем ждёт завершения.
        """
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

        while time.time() < deadline:
            data = self._get_json(f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}")
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

                # failed/cancelled/... -> download logs and extract error
                try:
                    zip_bytes = self._get_bytes(
                        f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs",
                        timeout=60,
                    )
                    files = self._unzip_logs(zip_bytes, max_total_chars=max_log_chars)
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

    # =========================
    # Internals
    # =========================

    def _wait_run_appears_by_sha(
        self,
        head_sha: str,
        deadline: float,
        poll_sec: int,
        per_page: int,
        event: Optional[str],
        workflow_name: Optional[str],
    ) -> Optional[dict[str, Any]]:
        params: dict[str, Any] = {
            "head_sha": head_sha,
            "per_page": min(max(per_page, 1), 100),
        }
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
                # берем самый свежий
                def ts(r: dict[str, Any]) -> str:
                    return (r.get("run_started_at") or r.get("created_at") or "")

                active = [r for r in runs if (r.get("status") or "").lower() != "completed"]
                if active:
                    return max(active, key=ts)
                return max(runs, key=ts)

            time.sleep(poll_sec)

        return None

    def _get_json(self, path: str, params: Optional[dict] = None, timeout: int = 20) -> dict:
        url = f"{self.api_base}{path}"
        r = self._session.get(url, params=params, timeout=timeout)
        if not r.ok:
            raise RuntimeError(f"GitHub API {r.status_code}: {self._safe_text(r)}")
        return r.json()

    def _get_bytes(self, path: str, params: Optional[dict] = None, timeout: int = 20) -> bytes:
        url = f"{self.api_base}{path}"
        r = self._session.get(url, params=params, timeout=timeout, allow_redirects=True)
        if not r.ok:
            raise RuntimeError(f"GitHub API {r.status_code}: {self._safe_text(r)}")
        return r.content

    @staticmethod
    def _safe_text(resp: requests.Response, limit: int = 2000) -> str:
        try:
            return (resp.text or "")[:limit]
        except Exception:
            return "<no response text>"

    # =========================
    # Logs parsing
    # =========================

    @staticmethod
    def _unzip_logs(zip_bytes: bytes, max_total_chars: int) -> list[tuple[str, str]]:
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
        rx = re.compile(
            r"(##\[error\]|traceback\b|exception\b|fatal\b|^\s*error\b|npm ERR!|yarn .*error|"
            r"gradle.*failed|failed\b|build\s+failed|compilation\s+failed|segmentation fault)",
            re.IGNORECASE,
        )

        best_score = -1
        best_snip: Optional[str] = None

        for fname, text in files:
            lines = text.splitlines()
            hits = [i for i, line in enumerate(lines) if rx.search(line)]
            if not hits:
                continue

            i = hits[-1]
            a = max(0, i - ctx_before)
            b = min(len(lines), i + ctx_after)
            snippet = "\n".join(lines[a:b]).strip()

            score = len(hits) * 1000 + (100 if "error" in fname.lower() else 0) + len(snippet) // 200
            if score > best_score:
                best_score = score
                best_snip = f"===== {fname} =====\n{snippet}"

        if best_snip:
            return best_snip

        if not files:
            return "(Логи пустые или не содержат txt/log файлов)"

        fname, text = max(files, key=lambda x: len(x[1]))
        tail_lines = text.splitlines()[-120:]
        return f"===== {fname} (tail) =====\n" + "\n".join(tail_lines).strip()
