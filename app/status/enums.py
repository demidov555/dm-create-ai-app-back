from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class AgentTask(str, Enum):
    NONE = "none"
    ANALYZING_SPEC = "analyzing_spec"
    GENERATING_CODE = "generating_code"
    VALIDATING_CODE = "validating_code"
    FINALIZING = "finalizing"


class ProjectStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class ProjectStage(Enum):
    PM_TZ = "pm_tz"
    ANALYSIS = "analysis"
    CODING = "coding"
    REPO_UPDATE = "repo_update"


PROJECT_STAGE_WEIGHTS = {
    ProjectStage.PM_TZ: 0.2,        # 20%
    ProjectStage.ANALYSIS: 0.1,     # 10%
    ProjectStage.CODING: 0.5,       # 50%
    ProjectStage.REPO_UPDATE: 0.2,  # 20%
}
