import functools

from grinmw.wallet_v3 import WalletV3, WalletError

from src.providers import WalletProvider

class WrapCoreWallet:
    def __init__(self, expected_length):
        self.expected_length = expected_length

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            other_self = args[0]
            try:
                other_self.wallet.open_wallet(None, other_self.wallet_password)
                ret = func(*args, **kwargs)
                other_self.wallet.close_wallet()
                return ret
            except WalletError as e:
                success = False
                reason = str(e)
                return tuple(
                    [success, reason] + [None for i in range(expected_length - 2)])
            except Exception as e:
                success = False
                return tuple(
                    [success] + [None for i in range(expected_length - 1)])
        return wrapper


class CoreWallet(WalletProvider):
    def __init__(self, api_password, api_host='http://127.0.0.1:3420/v3/owner', api_user='grin', wallet_password=''):
        self.api_user = api_user
        self.api_password = api_password
        self.api_host = api_host

        self.wallet_password = wallet_password

        # connect
        self.manageConnection()

    def manageConnection(self):
        self.wallet = WalletV3(self.api_url, self.api_user, self.api_password)

    # returns success (bool) reason (str)
    @WrapCoreWallet(2)
    def sync(self, start_height=0, delete_unconfirmed=False):
        self.wallet.scan(start_height=0, delete_unconfirmed=False)
        success = True
        reason = None
        return success, reason

    # returns success (bool) reason (str)
    @WrapCoreWallet(2)
    def isReady(self):
        ret = self.wallet.retrieve_summary_info()
        connected = ret[0]
        success = isinstance(connected, bool)
        reason = None
        return success, reason

    # returns success (bool) reason (str) slatepack (str) tx_id (str)
    @WrapCoreWallet(4)
    def send(self, amount, slatepack_address=None, minimum_confirmations=10, max_outputs=1, num_change_outputs=1):
        params = {
			'src_acct_name': None,
			'amount': amount,
			'minimum_confirmations': minimum_confirmations,
			'max_outputs': max_outputs,
			'num_change_outputs': num_change_outputs,
			'selection_strategy_is_use_all': True,
			'target_slate_version': None,
			'payment_proof_recipient_address': slatepack_address,
			'ttl_blocks': None,
			'send_args': None
		}
        slate = self.wallet.init_send_tx(params)
        fee = slate.get('fee', None)
        txid = slate.get('id', None)
        recipients = [slatepack_address]
        slatepack = self.wallet.create_slatepack_message(slate, recipients)
        success = True
        reason = None
        return success, reason, slatepack, txid

    # cancels the tx!
    # returns success (bool) reason (str)
    @WrapCoreWallet(2)
    def releaseLock(self, tx_id):
        self.wallet.cancel_tx(tx_slate_id=tx_id)
        success = True
        reason = None
        return success, reason

    # returns success (bool) reason (str), slatepack (str) tx_id (str)
    @WrapCoreWallet(4)
    def invoice(self, amount, slatepack_address=None, target_slate_version=None):
        params = {
			'amount': amount,
            'dest_acct_name': slatepack_address,
            'target_slate_version': None
		}
        slate = self.wallet.issue_invoice_tx(params)
        txid = slate.get('id', None)
        txid = grinUUIDtoBytes(txid)
        recipients = [] # TODO confirm this
        if slatepack_address is not None:
            recipients = [slatepack_address]
        slatepack = self.wallet.create_slatepack_message(slate, recipients)
        success = True
        reason = None
        return success, reason, slatepack, txid

    # returns success (bool) reason (str) slate (dict)
    @WrapCoreWallet(3)
    def decodeSlatepack(self, slatepack):
        secret_indices = [0]
        slate = self.wallet.slate_from_slatepack_message(slatepack, secret_indices)
        success = True
        reason = None
        return success, reason, slate

    # returns success (bool) reason (str), slatepack (str) tx_id (str)
    @WrapCoreWallet(4)
    def receive(self, slatepack):
        # for this we need to foreign API implemented
        # https://github.com/grinfans/grinmw.py only has owner
        # but I already have a fork and PR with foreign API
        # https://github.com/grinfans/grinmw.py/pull/7
        raise Exception('Unimplemented')

    # returns success (bool) reason (str), slatepack (str) tx_id (str)
    @WrapCoreWallet(3)
    def finalize(self, slatepack, lock=False, post=True, fluff=False):
        slate = self.wallet.slate_from_slatepack_message(slatepack, secret_indices)
        if lock:
            self.wallet.tx_lock_outputs(slate)
        slate_finalized = self.wallet.finalize_tx(slate)
        txid = slate_finalized.get('id', None)
        if post:
            post_res = self.broadcast(
                slate_finalized, open_wallet=False, fluff=fluff)
        success = True
        reason = None
        return success, reason, slatepack, txid
