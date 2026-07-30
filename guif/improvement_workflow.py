from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.improvement_cases import (
    CHANGE_TYPES,
    ImprovementCaseError,
    ImprovementCaseService,
)
from guif.source_workflow import (
    ConversationWorkflowService as SourceConversationWorkflowService,
)


class ConversationWorkflowService(SourceConversationWorkflowService):
    """Conversation workflow with private Candidate Change and Tool Trial lifecycles."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.improvements = ImprovementCaseService(
            self.workspace,
            runtime=self.runtime,
            data_root=self.store.layout.root,
        )

    def _active_improvement(
        self,
        session: dict[str, Any],
        *,
        sync: bool = True,
    ) -> dict[str, Any] | None:
        case_id = session.get("improvement_case_id")
        if not isinstance(case_id, str) or not case_id:
            return None
        try:
            case = self.improvements.store.get(
                str(session["project"]),
                case_id,
            )
        except ValueError:
            session.pop("improvement_case_id", None)
            return None
        if sync and case.get("status") == "candidate-running":
            case = self.improvements.sync_candidate_task(
                str(session["project"]),
                case_id,
            )
        return case

    @staticmethod
    def _improvement_actions(status: str) -> list[dict[str, Any]]:
        mapping: dict[str, list[dict[str, Any]]] = {
            "proposal-required": [
                {
                    "action": "improvement-propose",
                    "label": "完善候选改进方案",
                },
                {
                    "action": "improvement-cancel",
                    "label": "放弃改进并保留稳定版本",
                },
            ],
            "trial-approval-required": [
                {
                    "action": "improvement-trial-approve",
                    "label": "批准候选试验",
                },
                {
                    "action": "improvement-trial-request-changes",
                    "label": "调整试验方案",
                },
                {
                    "action": "improvement-trial-reject",
                    "label": "不进行试验",
                },
            ],
            "candidate-building": [
                {
                    "action": "improvement-development-handoff",
                    "label": "生成脱敏开发交接包",
                },
                {
                    "action": "improvement-candidate-link",
                    "label": "关联候选分支或版本",
                },
                {
                    "action": "improvement-adoption-reject",
                    "label": "放弃候选改进",
                },
            ],
            "candidate-ready": [
                {
                    "action": "improvement-candidate-run",
                    "label": "运行隔离候选试验",
                },
                {
                    "action": "improvement-result",
                    "label": "登记候选试验结果",
                },
                {
                    "action": "improvement-adoption-reject",
                    "label": "放弃候选改进",
                },
            ],
            "result-review-required": [
                {
                    "action": "improvement-adopt",
                    "label": "确认正式采用",
                },
                {
                    "action": "improvement-adoption-request-changes",
                    "label": "继续调整候选版本",
                },
                {
                    "action": "improvement-adoption-reject",
                    "label": "拒绝候选并保留稳定版本",
                },
            ],
            "publishing-required": [
                {
                    "action": "improvement-publish",
                    "label": "提交 PR、CI 并发布",
                }
            ],
            "plugin-refresh-required": [
                {
                    "action": "improvement-refresh-confirm",
                    "label": "刷新插件后继续",
                }
            ],
            "regression-validation-required": [
                {
                    "action": "improvement-regression-pass",
                    "label": "确认正式回归通过",
                },
                {
                    "action": "improvement-regression-fail",
                    "label": "回归失败并重新打开",
                },
            ],
            "resolved": [
                {
                    "action": "improvement-resume",
                    "label": "恢复原生产任务",
                }
            ],
            "closed-stable-retained": [
                {
                    "action": "improvement-resume",
                    "label": "保留稳定版本并恢复生产",
                }
            ],
        }
        return mapping.get(status, [])

    def _stage(
        self,
        session: dict[str, Any],
        task: Any | None,
    ) -> tuple[str, str, list[dict[str, Any]]]:
        case = self._active_improvement(session)
        if case is None:
            return super()._stage(session, task)

        status = str(case.get("status") or "")
        if status == "candidate-running":
            stage, message, actions = super()._stage(session, task)
            return (
                stage,
                "当前为隔离候选试验，稳定 GUIF 与正式配置尚未改变。"
                + message,
                actions,
            )

        messages = {
            "proposal-required": (
                "已暂停当前生产步骤并建立 GUIF 改进单。请先确认问题归因、候选修改、"
                "安全边界和真实结果验证方式。"
            ),
            "trial-approval-required": (
                "候选方案已经准备好。此处批准的只是隔离试验，不代表允许合并、发布"
                "或替换稳定版本。"
            ),
            "candidate-building": (
                "候选版本正在独立构建。不得修改已安装插件快照，也不得在看到真实候选"
                "结果前合并到 main。"
            ),
            "candidate-ready": (
                "候选版本或候选 Tool 已就绪，可以在稳定配置不变的前提下运行相同场景"
                "并收集真实结果。"
            ),
            "result-review-required": (
                "真实候选结果已经准备好。请比较稳定结果与候选结果，再决定正式采用、"
                "继续调整或放弃。"
            ),
            "publishing-required": (
                "用户已经确认采用候选改进。现在才能提交 Git、运行 CI、创建 PR 并在"
                "检查通过后合并。"
            ),
            "plugin-refresh-required": (
                "改进已经发布到 GUIF 源仓库。请刷新 Game UI Framework 插件并新建"
                " Codex 会话；旧会话不能假装热更新。"
            ),
            "regression-validation-required": (
                "插件版本已经满足要求。请重放原始问题场景并确认正式版本是否通过回归。"
            ),
            "resolved": (
                "候选改进已经采用并通过要求的验证，可以恢复原生产任务。"
            ),
            "closed-stable-retained": (
                "候选改进未被采用，稳定版本和正式 Tool 路由保持不变，可以恢复生产。"
            ),
        }
        stage_names = {
            "proposal-required": "improvement-proposal-required",
            "trial-approval-required": "improvement-trial-approval-required",
            "candidate-building": "improvement-candidate-building",
            "candidate-ready": "improvement-candidate-ready",
            "result-review-required": "improvement-result-review-required",
            "publishing-required": "improvement-publishing-required",
            "plugin-refresh-required": "plugin-refresh-required",
            "regression-validation-required": "regression-validation-required",
            "resolved": "improvement-resolved",
            "closed-stable-retained": "improvement-closed",
        }
        return (
            stage_names.get(status, "improvement-attention-required"),
            messages.get(
                status,
                "GUIF 改进单需要人工检查，原生产任务仍保持暂停。",
            ),
            self._improvement_actions(status),
        )

    def _public_view(
        self,
        session: dict[str, Any],
        *,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        payload = super()._public_view(
            session,
            include_diagnostics=include_diagnostics,
        )
        case = self._active_improvement(session)
        payload["improvement"] = (
            self.improvements.public_case(case)
            if isinstance(case, dict)
            else {
                "status": "not-active",
                "privacy": "private-outside-project-git",
            }
        )
        payload["production"] = {
            "paused_for_improvement": isinstance(case, dict)
            and case.get("status")
            not in {"resolved", "closed-stable-retained"},
            "stable_plugin_changed_by_trial": False,
        }
        return payload

    def open_improvement(
        self,
        project: str,
        conversation_id: str,
        *,
        change_type: str,
        observed_behavior: str,
        expected_behavior: str,
        diagnosis: str | None = None,
        proposal: dict[str, Any] | None = None,
        affected_tool_id: str | None = None,
        capability: str | None = None,
        adoption_scope: str = "project",
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        if change_type not in CHANGE_TYPES:
            raise ValueError("Unsupported GUIF Candidate Change type")
        session = self._session(project, conversation_id)
        active = self._active_improvement(session, sync=False)
        if active is not None and active.get("status") not in {
            "resolved",
            "closed-stable-retained",
        }:
            raise ImprovementCaseError(
                "This conversation already has an active Improvement Case"
            )
        task = self._load_active_task(session)
        case = self.improvements.open(
            project=project,
            conversation_id=conversation_id,
            task=task,
            checkpoint=session.get("checkpoint")
            if isinstance(session.get("checkpoint"), dict)
            else None,
            change_type=change_type,
            observed_behavior=observed_behavior,
            expected_behavior=expected_behavior,
            diagnosis=diagnosis,
            proposal=proposal,
            affected_tool_id=affected_tool_id,
            capability=capability,
            adoption_scope=adoption_scope,
            actor=actor,
        )
        session["improvement_case_id"] = case["case_id"]
        session["production_task_id"] = (
            task.task_id if task is not None else None
        )
        self._record(
            session,
            "improvement-opened",
            change_type=change_type,
        )
        self.store.save(session)
        return self._public_view(session)

    def improvement_status(
        self,
        project: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        return self._public_view(session)

    def propose_improvement(
        self,
        project: str,
        conversation_id: str,
        proposal: dict[str, Any],
        *,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.propose(
            project,
            str(case["case_id"]),
            proposal,
            actor=actor,
        )
        return self._public_view(session)

    def decide_improvement_trial(
        self,
        project: str,
        conversation_id: str,
        decision: str,
        *,
        comment: str | None = None,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.decide_trial(
            project,
            str(case["case_id"]),
            decision,
            actor=actor,
            comment=comment,
        )
        return self._public_view(session)

    def improvement_development_bundle(
        self,
        project: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        return self.improvements.development_bundle(
            project,
            str(case["case_id"]),
        )

    def link_improvement_candidate(
        self,
        project: str,
        conversation_id: str,
        candidate_data: dict[str, Any],
        *,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.link_candidate(
            project,
            str(case["case_id"]),
            candidate_data,
            actor=actor,
        )
        return self._public_view(session)

    def start_improvement_candidate(
        self,
        project: str,
        conversation_id: str,
        *,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        updated, task = self.improvements.start_tool_trial(
            project,
            str(case["case_id"]),
            actor=actor,
        )
        session["active_task_id"] = task.task_id
        session["candidate_task_active"] = True
        self._record(
            session,
            "improvement-candidate-started",
            change_type=updated.get("change_type"),
        )
        self.store.save(session)
        return self._public_view(session)

    def record_improvement_result(
        self,
        project: str,
        conversation_id: str,
        *,
        group: str,
        summary: str,
        file_path: Path | None = None,
        metadata: dict[str, Any] | None = None,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.record_result(
            project,
            str(case["case_id"]),
            group=group,
            summary=summary,
            file_path=file_path,
            metadata=metadata,
            actor=actor,
        )
        return self._public_view(session)

    def decide_improvement_adoption(
        self,
        project: str,
        conversation_id: str,
        decision: str,
        *,
        comment: str | None = None,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.decide_adoption(
            project,
            str(case["case_id"]),
            decision,
            actor=actor,
            comment=comment,
        )
        return self._public_view(session)

    def mark_improvement_published(
        self,
        project: str,
        conversation_id: str,
        delivery: dict[str, Any],
        *,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.mark_published(
            project,
            str(case["case_id"]),
            delivery,
            actor=actor,
        )
        return self._public_view(session)

    def confirm_improvement_refresh(
        self,
        project: str,
        conversation_id: str,
        *,
        current_plugin_version: str,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.confirm_refresh(
            project,
            str(case["case_id"]),
            current_plugin_version=current_plugin_version,
            actor=actor,
        )
        return self._public_view(session)

    def record_improvement_regression(
        self,
        project: str,
        conversation_id: str,
        *,
        passed: bool,
        summary: str,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        self.improvements.record_regression(
            project,
            str(case["case_id"]),
            passed=passed,
            summary=summary,
            actor=actor,
        )
        return self._public_view(session)

    def resume_after_improvement(
        self,
        project: str,
        conversation_id: str,
        *,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        case = self._active_improvement(session, sync=False)
        if case is None:
            raise ImprovementCaseError("No active Improvement Case")
        case = self.improvements.mark_resumed(
            project,
            str(case["case_id"]),
            actor=actor,
        )
        source = case.get("source_task")
        source_task_id = (
            str(source.get("task_id"))
            if isinstance(source, dict) and source.get("task_id")
            else None
        )
        if source_task_id:
            self.runtime.load_task(project, source_task_id)
            session["active_task_id"] = source_task_id
        session["last_improvement_case_id"] = case["case_id"]
        session.pop("improvement_case_id", None)
        session.pop("candidate_task_active", None)
        self._record(session, "improvement-production-resumed")
        self.store.save(session)
        return self._public_view(session)


__all__ = ["ConversationWorkflowService"]
