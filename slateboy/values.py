from enum import Enum


class UserBehavior(Enum):
    JOIN_GROUP = 0
    LEAVE_GROUP = 1
    DIRECT_MESSAGE = 2
    GROUP_MESSAGE = 3
    REQUEST_DEPOSIT = 4
    REQUEST_DEPOSIT_FIRST_TIME = 5
    INACTIVITY = 6


class BotBehavior(Enum):
    LAUNCHED = 0
