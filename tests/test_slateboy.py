import unittest
import warnings
import os

from i18n import resource_loader
from i18n import config as i18config
from i18n.translator import t

# from telegram.warning import TelegramDeprecationWarning
from unittest.mock import patch, Mock, MagicMock

from ptbtest import ChatGenerator
from ptbtest import MessageGenerator
from ptbtest import Mockbot
from ptbtest import UserGenerator
from ptbtest import CallbackQueryGenerator

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
        self.cqg = CallbackQueryGenerator(self.mock_bot)
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


    def interact(self, message, expected=None):
        update = self.mg.get_message(
            text=message,
            parse_mode='HTML',
            user=self.alice,
            chat=self.chat)
        return update


    def callbackQuery(self, sent_message, data):
        update = self.cqg.get_callback_query(
            message=sent_message,
            data=data,
            user=self.alice)
        return update


    # user tries the deposit, check if forced to see the EULA
    def testEULADisplay(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(True, 'very eula', 'eula_v1')):
                update = self.interact('/deposit')
                self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = 'very eula'
        self.assertEqual(response, expected_response)


    # check if slateboy will ignore the message if the personality
    # orders to do so
    def testIgnoredByPersonality(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                # personality orders to ignore this interaction
                ignore = True

                # case when the reason is known
                known_reason = 'very important reason'
                with patch('slateboy.personality.BlankPersonality.shouldIgnore',
                   return_value=(ignore, known_reason)):
                    update = self.interact('/deposit')
                    self.mock_bot.insertUpdate(update)
                sent = self.mock_bot.sent_messages[-1]
                response = sent['text']
                expected_response = known_reason
                self.assertEqual(response, expected_response)

                # case when the reason is not known
                unknown_reason = None
                with patch('slateboy.personality.BlankPersonality.shouldIgnore',
                   return_value=(ignore, unknown_reason)):
                    update = self.interact('/deposit')
                    self.mock_bot.insertUpdate(update)
                sent = self.mock_bot.sent_messages[-1]
                response = sent['text']
                expected_response = t('slateboy.msg_deposit_ignored_unknown')
                self.assertEqual(response, expected_response)


    # check if slateboy will indicate to use the slatepack directly in case
    # if user requests /deposit without providing the amount
    def testDepositMissingAmount(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                update = self.interact('/deposit')
                self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_missing_amount')
        self.assertEqual(response, expected_response)


    # check if slateboy will interrupt the deposit if personality
    # indicates the amount is not valid
    def testDepositInvalidAmount(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                update = self.interact('/deposit aaa')
                self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_invalid_amount')
        self.assertEqual(response, expected_response)


    # check if slateboy will interrupt the deposit if personality
    # indicates this user is not allowed to deposit and provides the reason
    def testDepositForbidden(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                success = True
                reason = 'because no'
                can_deposit = False
                approved_amount = 1000
                with patch('slateboy.personality.BlankPersonality.canDeposit',
                        return_value=(success, reason, can_deposit, approved_amount)):
                    update = self.interact('/deposit 12.3')
                    self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = reason
        self.assertEqual(response, expected_response)


    # check if slateboy will interrupt the deposit if personality
    # indicates this user is not allowed to deposit and provides the reason
    def testDepositForbiddenUnknownReason(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                success = True
                unknown_reason = None
                can_deposit = False
                approved_amount = 1000
                with patch('slateboy.personality.BlankPersonality.canDeposit',
                        return_value=(success, unknown_reason, can_deposit, approved_amount)):
                    update = self.interact('/deposit 12.3')
                    self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_rejected_known').format(
            '12.3', str(approved_amount))
        self.assertEqual(response, expected_response)


    def testBalance(self):
        # no balance at all
        success, reason, balance = True, None, (0.0, 0.0, 0.0, 0.0)
        with patch('slateboy.personality.BlankPersonality.getBalance',
                   return_value=(success, reason, balance)):
            update = self.interact('/balance')
            self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = 'Spendable: 0.0\n' \
            'Awaiting confirmation: 0.0\n' \
            'Awaiting finalization: 0.0\n' \
            'Locked: 0.0'
        self.assertEqual(response, expected_response)

        # spendable balance
        success, reason, balance = True, None, (12.0, 0.0, 0.0, 0.0)
        with patch('slateboy.personality.BlankPersonality.getBalance',
                   return_value=(success, reason, balance)):
            update = self.interact('/balance')
            self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = 'Spendable: 12.0\n' \
            'Awaiting confirmation: 0.0\n' \
            'Awaiting finalization: 0.0\n' \
            'Locked: 0.0'
        self.assertEqual(response, expected_response)

        # a bit of everything
        success, reason, balance = True, None, (8.0, 19.0, 3.0, 2.0)
        with patch('slateboy.personality.BlankPersonality.getBalance',
                   return_value=(success, reason, balance)):
            update = self.interact('/balance')
            self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = 'Spendable: 8.0\n' \
            'Awaiting confirmation: 19.0\n' \
            'Awaiting finalization: 3.0\n' \
            'Locked: 2.0'
        self.assertEqual(response, expected_response)


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
