class WalletProvider:
    # returns success (bool) reason (str)
    def sync(self):
        raise Exception('Unimplemented')

    # returns boolean
    def isReady(self):
        raise Exception('Unimplemented')

    # returns slatepack, tx_id
    def send(self, amount, slatepack_address=None):
        raise Exception('Unimplemented')

    # returns success (bool) reason (str)
    def releaseLock(self, tx_id):
        raise Exception('Unimplemented')

    # returns success (bool) reason (str), slatepack (str) tx_id (str)
    def invoice(self, amount, slatepack_address=None):
        raise Exception('Unimplemented')

    # returns slate (dict)
    def decodeSlatepack(self, slatepack):
        raise Exception('Unimplemented')

    # returns success (bool) reason (str), slatepack (str) tx_id (str)
    def receive(self, slatepack):
        raise Exception('Unimplemented')

    # returns success (bool) reason (str), slatepack (str)
    def finalize(self, slatepack):
        raise Exception('Unimplemented')



