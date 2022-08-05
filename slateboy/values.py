from enum import Enum


class ContextUserInitiate(Enum):
    MESSAGE = 0
    JOIN = 1


class ContextUserDestroy(Enum):
    NEVER = 0
    LEFT_WITHOUT_BALANCE = 1
    INACTIVITY_WITHOUT_BALANCE = 2


class TermsAndConditionsApproval(Enum):
    NEVER = 0
    FIRST_DEPOSIT = 1
    EVERY_DEPOSIT = 2
