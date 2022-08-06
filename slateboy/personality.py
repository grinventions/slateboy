class BlankPersonality:
    def __init__(self, slateboy):
        self.slateboy = slateboy

    # deposit behavior
    def canDeposit(self, update, context):
        pass

    def finalizeDeposit(self, update, context):
        pass

    def cancelDeposit(self, context, update=False):
        pass

    # withdraw behavior
    def canWithdraw(self, update, context):
        pass

    def finalizeWithdraw(self, update, context):
        pass

    def cancelWithdraw(self, context, update=None):
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
