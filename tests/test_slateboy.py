import unittest
import warnings
import os

from i18n import resource_loader
from i18n import config as i18config

# from telegram.warning import TelegramDeprecationWarning
from unittest.mock import patch, Mock, MagicMock

from ptbtest import ChatGenerator
from ptbtest import MessageGenerator
from ptbtest import Mockbot
from ptbtest import UserGenerator

from slateboy.slateboy import SlateBoy
from slateboy.personality import BlankPersonality
from slateboy.providers import WalletProvider

TRANSLATIONS_DIRECTORY = os.path.dirname(os.path.abspath(__file__)) + os.sep + '../translations' + os.sep
i18config.set('file_format', 'json')
i18config.set('load_path', [TRANSLATIONS_DIRECTORY])
i18config.set('filename_format', '{namespace}.{locale}.{format}')
i18config.set('locale', 'en')
resource_loader.init_json_loader()


class TestSlateBoy(unittest.TestCase):
    def setUp(self):
        # ignore TelegramDeprecationWarning
        warnings.simplefilter('ignore')
        # the mocked bot
        self.mock_bot = Mockbot()
        # generators for users and chats
        self.ug = UserGenerator()
        self.cg = ChatGenerator()
        # actors and chats
        self.chat = self.cg.get_chat()
        self.alice = self.ug.get_user()
        # message generator and updater (for use with the bot.)
        self.mg = MessageGenerator(self.mock_bot)
        # slateboy
        self.personality = BlankPersonality()
        self.wallet_provider = WalletProvider()
        self.slateboy = SlateBoy(
            'slate-boy', '',
            self.personality, self.wallet_provider, bot=self.mock_bot)
        self.slateboy.initiate()
        self.slateboy.run(idle=False)


    def tearDown(self):
        self.slateboy.stop()


    def interact(self, message):
        nb_messages = len(self.mock_bot.sent_messages)
        update = self.mg.get_message(
                text='/balance', parse_mode='HTML', user=self.alice, chat=self.chat)
        self.mock_bot.insertUpdate(update)
        self.assertEqual(len(self.mock_bot.sent_messages), nb_messages + 1)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        return response


    def testDeposit(self):
        # user checks balance, there is nothing
        success, reason, balance = True, None, (0.0, 0.0, 0.0, 0.0)
        with patch('slateboy.personality.BlankPersonality.getBalance',
                   return_value=(success, reason, balance)):
            response = self.interact('/balance')
            expected_response = 'Spendable: 0.0\n' \
                'Awaiting confirmation: 0.0\n' \
                'Awaiting finalization: 0.0\n' \
                'Locked: 0.0'
            self.assertEqual(response, expected_response)

        # user tries the deposit is forced to see the EULA
        # user checks balance, there is nothing
        # user denies the EULA
        # user checks balance, there is nothing
        # user tries the deposit, is forced to see the EULA again
        # user checks balance, there is nothing
        # user approves the EULA
        # user checks balance, there is nothing
        # user tries the deposit, gets slatepack
        # user checks balance, there amount pending finalization
        # user responds with the slatepack
        # user checks balance, there amount pending confirmation
        pass

    # we need to introduce variations of the deposit test:
    # - deposit using just a slatepack
    # - deposit without specifying the amount should fail and result with
    # receiving the instructions


    def testWithdraw(self):
        # user checks balance, there is some spendable balance
        # user tries withdrawal, requests too much and fails
        # user checks balance, there is some spendable balance
        # user tries withdrawal, requests less than the balance receives slatepack
        # user checks balance, there is some spendable and locked balance
        # user responds with the slatepack
        # user checks balance, there is some spendable and locked balance
        pass

    # we need to introduce variations of the withdraw test:
    # - withdraw with 'max' instead of the amount
    # - withdraw without specifying the amount, should work as 'max'


    def testDepositConfirmed(self):
        # user checks balance, there amount pending confirmation
        # bot finds that the tx_id is confirmed
        # user gets notified
        # user checks balance, there amount is now spendable
        pass


    def testDepositCanceled(self):
        # user checks balance, there amount pending finalization
        # bot finds that the tx_id is old and cancels it
        # user gets notified
        # user checks balance, there nothing
        pass


    def testWithdrawConfirmed(self):
        # user checks balance, there is some spendable and locked balance
        # bot finds that the tx_id is confirmed
        # user gets notified
        # user checks balance, there is only spendable balance now
        pass


    def testWithdrawCanceled(self):
        # user checks balance, there amount locked
        #user did not respond with slatepack

        # bot finds that the tx_id is old and cancels it
        # user gets notified
        # user checks balance, the locked amount is back in spendable
        pass

    def testWalletSyncs(self):
        # test if wallet sync method gets called
        pass
