class BlankPersonality:
    def __init__(self, slateboy):
        self.slateboy = slateboy

    # getting the balance
    # returns one of the following types
    #
    # (int, int, int)
    # (spendable, confirming, locked)
    # then it is assumed to be GRIN in IGNO unit
    #
    # (float, float, float)
    # (spendable, confirming, locked)
    # then it is assumed to be GRIN in whole GRIN units
    #
    # str
    # formatted balance text ready for the user
    def getBalance(self, update, context):
        pass

    # deposit behavior

    # (bool, str)
    # bool indicates whether user can deposit the amount
    # str is the formatted message to the user
    def canDeposit(self, update, context, amount):
        pass

    # puts amount as awaiting_finalization balance
    # returns (str)
    # str is the formatted message to the user
    # it can contain {slatepack} tag to put the slatepack
    # inside of it, if the tag is not included, the slatepack
    # will be sent in the separate message
    def assignDepositTx(self, update, context, amount tx_id):
        pass

    # puts amount as awaiting_confirmation balance
    # returns (str)
    # str is the formatted message to the user
    def finalizeDepositTx(self, update, context, amount, tx_id):
        pass

    # is called if user does not "pay" on time
    # removes amount from awaiting_finalization balance
    def cancelDeposit(self, context, amount, tx_id, update=False):
        pass

    # withdraw behavior

    # (bool, str)
    # bool indicates whether user can withdraw the amount
    # str is the formatted message to the user
    def canWithdraw(self, update, context, amount):
        pass

    # moves amount from spendable balance to locked balance
    # returns (str)
    # str is the formatted message to the user
    # it can contain {slatepack} tag to put the slatepack
    # inside of it, if the tag is not included, the slatepack
    # will be sent in the separate message
    def assignWithdrawTx(self, update, context, tx_id):
        pass

    # does not move any balance but it is a chance to format message
    # to the user
    # returns (str)
    # str is the formatted message to the user
    def finalizeWithdraw(self, update, context, amount, tx_id):
        pass

    # is called if user does not "receive" on time
    # moves amount from locked back to spendable
    def cancelWithdraw(self, context, amount, tx_id, update=None):
        pass

    # EULA behavior
    def shouldSeeEULA(self, update, context):
        return False

    def approvedEULA(self, update, context):
        pass

    def deniedEULA(self, update, context):
        pass

    # what to do if being added to the group, should leave it?
    def shouldLeave(self, update, context):
        return False

    # what to do if being messaged, should ignore?
    def shouldIgnore(self, update, context):
        return False

    # callback informing that bot left the group
    def leftGroup(self, update, context):
        pass

    # callback about incoming text
    def incomingText(self, update, context):
        pass

    # renaming standard commands
    def renameStandardCommands(self):
        return []

    # registering custom commands
    def registerCustomCommands(self):
        return []

    # register custom jobs
    def registerCustomJobs(self):
        return []
