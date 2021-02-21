"""authentik stage Base view"""
from typing import Any, Optional

from django.http import HttpRequest
from django.http.request import QueryDict
from django.http.response import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from structlog.stdlib import get_logger

from authentik.core.models import User
from authentik.flows.challenge import (
    Challenge,
    ChallengeResponse,
    HttpChallengeResponse,
)
from authentik.flows.planner import PLAN_CONTEXT_PENDING_USER
from authentik.flows.views import FlowExecutorView

PLAN_CONTEXT_PENDING_USER_IDENTIFIER = "pending_user_identifier"
LOGGER = get_logger()


class StageView(TemplateView):
    """Abstract Stage, inherits TemplateView but can be combined with FormView"""

    template_name = "login/form_with_user.html"

    executor: FlowExecutorView

    request: HttpRequest = None

    def __init__(self, executor: FlowExecutorView):
        self.executor = executor

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        kwargs["title"] = self.executor.flow.title
        # Either show the matched User object or show what the user entered,
        # based on what the earlier stage (mostly IdentificationStage) set.
        # _USER_IDENTIFIER overrides the first User, as PENDING_USER is used for
        # other things besides the form display
        if PLAN_CONTEXT_PENDING_USER in self.executor.plan.context:
            kwargs["user"] = self.executor.plan.context[PLAN_CONTEXT_PENDING_USER]
        if PLAN_CONTEXT_PENDING_USER_IDENTIFIER in self.executor.plan.context:
            kwargs["user"] = User(
                username=self.executor.plan.context.get(
                    PLAN_CONTEXT_PENDING_USER_IDENTIFIER
                ),
                email="",
            )
        kwargs["primary_action"] = _("Continue")
        return super().get_context_data(**kwargs)


class ChallengeStageView(StageView):
    """Stage view which response with a challenge"""

    response_class = ChallengeResponse

    def get_pending_user(self) -> Optional[User]:
        """Either show the matched User object or show what the user entered,
        based on what the earlier stage (mostly IdentificationStage) set.
        _USER_IDENTIFIER overrides the first User, as PENDING_USER is used for
        other things besides the form display"""
        if PLAN_CONTEXT_PENDING_USER_IDENTIFIER in self.executor.plan.context:
            return User(
                username=self.executor.plan.context.get(
                    PLAN_CONTEXT_PENDING_USER_IDENTIFIER
                ),
                email="",
            )
        if PLAN_CONTEXT_PENDING_USER in self.executor.plan.context:
            return self.executor.plan.context[PLAN_CONTEXT_PENDING_USER]
        return None

    def get_response_instance(self, data: QueryDict) -> ChallengeResponse:
        """Return the response class type"""
        return self.response_class(None, data=data, stage=self)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        challenge = self.get_challenge(*args, **kwargs)
        if "title" not in challenge.initial_data:
            challenge.initial_data["title"] = self.executor.flow.title
        if not challenge.is_valid():
            LOGGER.warning(challenge.errors)
        return HttpChallengeResponse(challenge)

    # pylint: disable=unused-argument
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Handle challenge response"""
        challenge: ChallengeResponse = self.get_response_instance(data=request.POST)
        if not challenge.is_valid():
            return self.challenge_invalid(challenge)
        return self.challenge_valid(challenge)

    def get_challenge(self, *args, **kwargs) -> Challenge:
        """Return the challenge that the client should solve"""
        raise NotImplementedError

    def challenge_valid(self, response: ChallengeResponse) -> HttpResponse:
        """Callback when the challenge has the correct format"""
        raise NotImplementedError

    def challenge_invalid(self, response: ChallengeResponse) -> HttpResponse:
        """Callback when the challenge has the incorrect format"""
        challenge_response = self.get_challenge()
        challenge_response.initial_data["title"] = self.executor.flow.title
        full_errors = {}
        for field, errors in response.errors.items():
            for error in errors:
                full_errors.setdefault(field, [])
                full_errors[field].append(
                    {
                        "string": str(error),
                        "code": error.code,
                    }
                )
        challenge_response.initial_data["response_errors"] = full_errors
        if not challenge_response.is_valid():
            LOGGER.warning(challenge_response.errors)
        return HttpChallengeResponse(challenge_response)
