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


example_slatepack = '''
BEGINSLATEPACK. 4H1qx1wHe668tFW yC2gfL8PPd8kSgv
pcXQhyRkHbyKHZg GN75o7uWoT3dkib R2tj1fFGN2FoRLY
GWmtgsneoXf7N4D uVWuyZSamPhfF1u AHRaYWvhF7jQvKx
wNJAc7qmVm9JVcm NJLEw4k5BU7jY6S eb. ENDSLATEPACK
'''

example_slate_s1 = {
    'ver': '4:2',
    'id': '0436430c-2b02-624c-2032-570501212b00',
    'sta': 'S1',
    'off': 'd202964900000000d302964900000000d402964900000000d502964900000000',
    'amt': '6000000000',
    'fee': '8000000',
    'sigs': [
        {
            'xs': '023878ce845727f3a4ec76ca3f3db4b38a2d05d636b8c3632108b857fed63c96de',
            'nonce': '031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f',
        }
    ]
}

example_slate_s2 = {
    'ver': '4:3',
    'id': '0436430c-2b02-624c-2032-570501212b00',
    'sta': 'S2',
    'off': 'a4052c9200000001a6052c9200000002ed564fab50b75fc5ea32ce052fc9bebf',
    'sigs': [
        {
            'xs': '03b0d73a044f1f9ae06cf96ef91593f121864b66bf7f7e7ac481b0ce61e39847fe',
            'nonce': '031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f',
            'part': '8f07ddd5e9f5179cff19486034181ed76505baaad53e5d994064127b56c5841b54735cb9ed2f59fb457144f7b1c8226d08b54cbdd0eb7e6492950751b0bb54f9'
        }
    ],
    'coms': [
        {
            'c': '091582c92b99943b57955e52b5ccf1223780c2a2e55995c00c86fca2bcb46b6b9f',
            'p': '49972a8d5b7c088e7813c3988ebe0982f8f0b12b849b1788df7da07b549408b0d6c99f80c0e2335370c104225ef5d282d79966e9044c959bedc3be03af6246fa07fc13eb3c60c90213c9f3a7a5ecf9a34c8fbaddc1a72e49e12dba9495e5aaa53bb6ac6ed63d8774707c57ab604d6bdc46de18da57a731fe336c3ccef92b4dae967417ffdae2c7d75864d46d30e287dd9cc15882e15f296b9bab0040e4432f4024be33924f112dd26c90cc800ac09a327b0ac3a661f63da9945fb1bcc82a7777d61d97cbe657675e22d035d2cf9ea03a89cfa410960ebc18a0a18b1909f4c5bef20b0fd13ffcf5a818ad8768d354b1c0f2e9b16dd7a9cf0641546f57d1945a98b8684d067dd085b90b40457e4c14665fb1b94feecf30a90f508ded16ba1bba8080a6866dffd0b1f01738fff8c62ce5e38e677835752a1b4072124dd9ff14ba8ff92126baebbb5f6e14fbb052f5d5b09aec11bfd880d7d4640a295aa83f184034d26f00cbdbabf9b89fddd7a7c9cc8c5d4b53fc39971e4495a8d984ac9607be89780fde528ee3f2d6b912908b4caf04f5c93f64431517af6b32d0b9c18255959f6903c6696ec71f615a0c877630a2d871f3f8a107fc80f306a94b6ad5790070f7d2535163bad7feae9263a9d3558ea1acecc4e61ff4e05b0162f6aba1a3b299ff1c3bb85e4109e550ad870c328bedc45fed8b504f679bc3c1a25b2b65ede44602f21fac123ba7c5f132e7c786bf9420a27bae4d2559cf7779e77f96b747b6d3ad5c13b5e8c9b49a7083001b2f98bcf242d4644537bb5a3b5b41764812a93395b7ab372c18be575e02c3763b4170234e5fddeb43420aadb71cb80f75cc681c1e7ffee3e6a8868c6076fd1da539ab9a12fef1c8cbe271b6de60100c9f82d826dc97b47b57ee9804e60112f556c1dce4f12ecc91ef34d69090b8c9d2ae9cbae38994a955cb'
        }
    ]
}

example_slate_i1 = {
    'ver': '4:3',
    'id': '0436430c-2b02-624c-2032-570501212b00',
    'sta': 'I1'
}

example_slate_i2 = {
    'ver': '4:3',
    'id': '0436430c-2b02-624c-2032-570501212b00',
    'sta': 'I2'
}


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
        self.group = self.cg.get_chat(type='group')
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


    def interact(self, message, group=False):
        w = self.chat
        if group:
            w = self.group
        update = self.mg.get_message(
            text=message,
            parse_mode='HTML',
            user=self.alice,
            chat=w)
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


    # check if slateboy will interrupt the deposit if the wallet
    # fails to initiate the invoice flow
    def testDepositWalletInvoiceFlowFailure(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                success = True
                unknown_reason = None
                can_deposit = True
                approved_amount = 1000
                with patch('slateboy.personality.BlankPersonality.canDeposit',
                        return_value=(success, unknown_reason, can_deposit, approved_amount)):
                    success = False
                    reason = 'wallet not workin :/'
                    slatepack = None
                    tx_id = None
                    with patch('slateboy.providers.WalletProvider.invoice',
                          return_value=(success, reason, slatepack, tx_id)):
                        update = self.interact('/deposit 12.3')
                        self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = reason
        self.assertEqual(response, expected_response)


    # check if slateboy will interrupt the deposit if the wallet
    # wallet succeeds but the personality fails to register the tx
    def testDepositPersonalityFlowFailure(self):
        with patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None)):
            with patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1')):
                success = True
                unknown_reason = None
                can_deposit = True
                approved_amount = 1000
                with patch('slateboy.personality.BlankPersonality.canDeposit',
                        return_value=(success, unknown_reason, can_deposit, approved_amount)):
                    success = True
                    reason = None
                    slatepack = '<mr slatepack>'
                    tx_id = '<txid>'
                    with patch('slateboy.providers.WalletProvider.invoice',
                          return_value=(success, reason, slatepack, tx_id)):
                        success = False
                        reason = 'dunno something ricked'
                        send_instructions = 'None'
                        msg = None
                        with patch('slateboy.personality.BlankPersonality.assignDepositTx',
                                   return_value=(success, reason, send_instructions, msg)):
                            with patch('slateboy.providers.WalletProvider.releaseLock'):
                                update = self.interact('/deposit 12.3')
                                self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = reason
        self.assertEqual(response, expected_response)

    # no instructions and standard slatepack formatting and final message
    def testCompleteFinancialOperationCase1(self):
        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))
        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))
        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, None, True, 1000))
        slatepack = '<mr slatepack>'
        P4 = patch('slateboy.providers.WalletProvider.invoice',
                   return_value=(True, None, slatepack, '<txid>'))
        P5 = patch('slateboy.personality.BlankPersonality.assignDepositTx',
                   return_value=(True, None, None, None))
        send_instructions = False
        custom_instructions = None
        P6 = patch('slateboy.personality.BlankPersonality.customDepositInstructions',
                   return_value=(send_instructions, custom_instructions))
        custom_slatepack_formatting = None
        P7 = patch('slateboy.personality.BlankPersonality.customDepositSlatepackFormatting',
                   return_value=(custom_slatepack_formatting))
        final_message = 'Some final few words'
        P8 = patch('slateboy.personality.BlankPersonality.customDepositFinalMessage',
                   return_value=(final_message))
        with P1, P2, P3, P4, P5, P6, P7, P8:
            update = self.interact('/deposit 12.3')
            self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-2]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_slatepack_formatting').format(**{
            'slatepack': slatepack
        })
        self.assertEqual(response, expected_response)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = final_message
        self.assertEqual(response, expected_response)

    # standard instructions and custom slatepack formatting and no final message
    def testCompleteFinancialOperationCase2(self):
        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))
        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))
        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, None, True, 1000))
        slatepack = '<mr slatepack>'
        P4 = patch('slateboy.providers.WalletProvider.invoice',
                   return_value=(True, None, slatepack, '<txid>'))
        P5 = patch('slateboy.personality.BlankPersonality.assignDepositTx',
                   return_value=(True, None, None, None))
        send_instructions = True
        custom_instructions = None
        P6 = patch('slateboy.personality.BlankPersonality.customDepositInstructions',
                   return_value=(send_instructions, custom_instructions))
        custom_slatepack_formatting = None
        P7 = patch('slateboy.personality.BlankPersonality.customDepositSlatepackFormatting',
                   return_value=(custom_slatepack_formatting))
        final_message = None
        P8 = patch('slateboy.personality.BlankPersonality.customDepositFinalMessage',
                   return_value=(final_message))
        with P1, P2, P3, P4, P5, P6, P7, P8:
            update = self.interact('/deposit 12.3')
            self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-2]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_instructions')
        self.assertEqual(response, expected_response)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_slatepack_formatting').format(**{
            'slatepack': slatepack
        })
        self.assertEqual(response, expected_response)

    # custom instructions and custom slatepack formatting and no final message
    def testCompleteFinancialOperationCase3(self):
        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))
        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))
        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, None, True, 1000))
        slatepack = '<mr slatepack>'
        P4 = patch('slateboy.providers.WalletProvider.invoice',
                   return_value=(True, None, slatepack, '<txid>'))
        P5 = patch('slateboy.personality.BlankPersonality.assignDepositTx',
                   return_value=(True, None, None, None))
        send_instructions = True
        custom_instructions = 'custom instructions'
        P6 = patch('slateboy.personality.BlankPersonality.customDepositInstructions',
                   return_value=(send_instructions, custom_instructions))
        custom_slatepack_formatting = None
        P7 = patch('slateboy.personality.BlankPersonality.customDepositSlatepackFormatting',
                   return_value=(custom_slatepack_formatting))
        final_message = None
        P8 = patch('slateboy.personality.BlankPersonality.customDepositFinalMessage',
                   return_value=(final_message))
        with P1, P2, P3, P4, P5, P6, P7, P8:
            update = self.interact('/deposit 12.3')
            self.mock_bot.insertUpdate(update)
        sent = self.mock_bot.sent_messages[-2]
        response = sent['text']
        expected_response = custom_instructions
        self.assertEqual(response, expected_response)
        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']
        expected_response = t('slateboy.msg_deposit_slatepack_formatting').format(**{
            'slatepack': slatepack
        })
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

    def test_contains_slatepack(self):
        some_message = '''
        and then I tell him bla bla bla
        '''
        some_message += example_slatepack + '\n'
        some_message += '''
        and lol bro lmao xD
        '''
        contains_slatepack, extracted_slatepack = self.slateboy.containsSlatepack(
            some_message)
        expected_slatepack = example_slatepack.replace('\n', '')
        self.assertTrue(contains_slatepack)
        self.assertEqual(extracted_slatepack, expected_slatepack)

        some_message = 'ho ho ho merry christmas!'
        contains_slatepack, extracted_slatepack = self.slateboy.containsSlatepack(
            some_message)
        self.assertFalse(contains_slatepack)
        self.assertEqual(extracted_slatepack, None)

    # message is ordered to be ignored by the personality
    def test_text_message_case1(self):
        some_message = 'you ***********'

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        shall_continue = False
        reason = 'because not!'
        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(shall_continue, reason))

        with P1, P2:
            update = self.interact(some_message)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        self.assertEqual(response, reason)

    # message is ordered to be ignored by the personality because it is a group
    # message
    def test_text_message_case2(self):
        some_message = 'you ***********'

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        shall_continue = False
        reason = 'because not!'
        P3 = patch('slateboy.personality.BlankPersonality.incomingTextGroup',
                return_value=(shall_continue, reason))

        with P1, P2, P3:
            update = self.interact(some_message, group=True)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        self.assertEqual(response, reason)

    # message is ordered to be ignored by the personality for a specific case
    # of a direct message
    def test_text_message_case3(self):
        some_message = 'you ***********'

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        shall_continue = False
        reason = 'because not!'
        P3 = patch('slateboy.personality.BlankPersonality.incomingTextDM',
                return_value=(shall_continue, reason))

        with P1, P2, P3:
            update = self.interact(some_message, group=False)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        self.assertEqual(response, reason)

    # group message with a slatepack should be ignored
    def test_text_message_case4(self):
        some_message = example_slatepack

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        P3 = patch('slateboy.personality.BlankPersonality.incomingTextGroup',
                return_value=(True, None))

        custom_public_slatepack_warning = 'pls don do that!'
        P4 = patch('slateboy.personality.BlankPersonality.customPublicSlatepackWarning',
                return_value=custom_public_slatepack_warning)

        with P1, P2, P3, P4:
            update = self.interact(some_message, group=True)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        self.assertEqual(response, custom_public_slatepack_warning)

    # a DM message containing a slatepack that is a deposit
    def test_text_message_deposit(self):

        some_message = example_slatepack

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        P3 = patch('slateboy.personality.BlankPersonality.incomingTextGroup',
                return_value=(False, None))

        slate = example_slate_s1
        P4 = patch('slateboy.providers.WalletProvider.decodeSlatepack',
                return_value=slate)

        reply_text = 'cowabangaaaa'
        def mockedProcessS1Slatepack(_self, update, context, slatepack, tx_id):
            chat_id = update.message.chat.id
            context.bot.send_message(chat_id=chat_id, text=reply_text)

        P5 = patch('slateboy.slateboy.SlateBoy.processS1Slatepack',
                mockedProcessS1Slatepack)

        with P1, P2, P3, P4, P5:
            update = self.interact(some_message)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        expected_reply_text = reply_text
        self.assertEqual(response, expected_reply_text)

    # a DM message containing a slatepack response for the withdrawal
    def test_text_message_withdrawal(self):

        some_message = example_slatepack

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        P3 = patch('slateboy.personality.BlankPersonality.incomingTextGroup',
                return_value=(False, None))

        slate = example_slate_s2
        P4 = patch('slateboy.providers.WalletProvider.decodeSlatepack',
                return_value=slate)

        reply_text = 'cowabangaaaa'
        def mockedProcessS2Slatepack(_self, update, context, slatepack, tx_id):
            chat_id = update.message.chat.id
            context.bot.send_message(chat_id=chat_id, text=reply_text)

        P5 = patch('slateboy.slateboy.SlateBoy.processS2Slatepack',
                mockedProcessS2Slatepack)

        with P1, P2, P3, P4, P5:
            update = self.interact(some_message)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        expected_reply_text = reply_text
        self.assertEqual(response, expected_reply_text)

    # a DM message containing an unexpected receipt
    def test_text_message_unexpected_receipt(self):

        some_message = example_slatepack

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        P3 = patch('slateboy.personality.BlankPersonality.incomingTextGroup',
                return_value=(False, None))

        slate = example_slate_i1
        P4 = patch('slateboy.providers.WalletProvider.decodeSlatepack',
                return_value=slate)

        with P1, P2, P3, P4:
            update = self.interact(some_message)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        expected_reply_text = t('slateboy.msg_ignoring_invoices')
        self.assertEqual(response, expected_reply_text)

    # a DM message containing a slatepack response to deposit invoice
    def test_text_message_deposit_invoice_response(self):

        some_message = example_slatepack

        ignore = False
        P1 = patch('slateboy.personality.BlankPersonality.shouldIgnore',
                return_value=(ignore, None))

        P2 = patch('slateboy.personality.BlankPersonality.incomingText',
                return_value=(True, None))

        P3 = patch('slateboy.personality.BlankPersonality.incomingTextGroup',
                return_value=(False, None))

        slate = example_slate_i2
        P4 = patch('slateboy.providers.WalletProvider.decodeSlatepack',
                return_value=slate)

        reply_text = 'cowabangaaaa'
        def mockedProcessI2Slatepack(_self, update, context, slatepack, tx_id):
            chat_id = update.message.chat.id
            context.bot.send_message(chat_id=chat_id, text=reply_text)

        P5 = patch('slateboy.slateboy.SlateBoy.processI2Slatepack',
                mockedProcessI2Slatepack)

        with P1, P2, P3, P4, P5:
            update = self.interact(some_message)
            print()
            print(update)
            self.mock_bot.insertUpdate(update)

        sent = self.mock_bot.sent_messages[-1]
        response = sent['text']

        expected_reply_text = reply_text
        self.assertEqual(response, expected_reply_text)


    # test processS1Slatepack with invalid amount
    def test_processS1Slatepack_invalid_amount(self):
        update = MagicMock()
        update.message.chat.id = 0
        update.message.from_user.id = 0

        context = MagicMock()
        context.bot.send_message.return_value = True

        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        slate = {
            'ver': '4:3',
            'id': tx_id,
            'sta': 'S1'
        }

        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))

        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))

        with P1, P2:
            self.slateboy.processS1Slatepack(update, context, slate, tx_id)
            expected = t('slateboy.msg_invalid_slatepack')
            context.bot.send_message.assert_called_with(chat_id=0, text=expected)

    # test processS1Slatepack with personality rejection
    def test_processS1Slatepack_personality_rejected(self):
        update = MagicMock()
        update.message.chat.id = 0
        update.message.from_user.id = 0

        context = MagicMock()
        context.bot.send_message.return_value = True

        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        slate = {
            'ver': '4:3',
            'id': tx_id,
            'sta': 'S1',
            'amt': 320000
        }

        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))

        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))

        reason = 'no way Jose'
        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, reason, False, 300000))

        with P1, P2, P3:
            shall_continue = self.slateboy.processS1Slatepack(update, context, slate, tx_id)
            context.bot.send_message.assert_called_with(chat_id=0, text=reason)
            assert shall_continue == False

    # test processS1Slatepack with a wallet failure
    def test_processS1Slatepack_wallet_failure(self):
        update = MagicMock()
        update.message.chat.id = 0
        update.message.from_user.id = 0

        context = MagicMock()
        context.bot.send_message.return_value = True

        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        slate = {
            'ver': '4:3',
            'id': tx_id,
            'sta': 'S1',
            'amt': 320000
        }

        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))

        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))

        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, None, True, 320000))

        reason = 'no way Jose'
        P4 = patch('slateboy.providers.WalletProvider.receive',
                   return_value=(False, reason, 'slatepack', 'tx_id'))

        with P1, P2, P3, P4:
            shall_continue = self.slateboy.processS1Slatepack(update, context, slate, tx_id)
            context.bot.send_message.assert_called_with(chat_id=0, text=reason)
            assert shall_continue == False

    # test processS1Slatepack with a personality failure to create the deposit
    def test_processS1Slatepack_personality_deposit_failure(self):
        update = MagicMock()
        update.message.chat.id = 0
        update.message.from_user.id = 0

        context = MagicMock()
        context.bot.send_message.return_value = True

        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        slate = {
            'ver': '4:3',
            'id': tx_id,
            'sta': 'S1',
            'amt': 320000
        }

        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))

        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))

        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, None, True, 320000))

        P4 = patch('slateboy.providers.WalletProvider.receive',
                   return_value=(True, None, 'slatepack', 'tx_id'))

        reason = 'no way Jose'
        P5 = patch('slateboy.personality.BlankPersonality.assignDepositTx',
                   return_value=(False, reason, 'instructions', 'msg'))

        P6 = patch('slateboy.providers.WalletProvider.releaseLock',
                   return_value=(True))

        with P1, P2, P3, P4, P5, P6:
            shall_continue = self.slateboy.processS1Slatepack(update, context, slate, tx_id)
            context.bot.send_message.assert_called_with(chat_id=0, text=reason)
            assert shall_continue == False

    # test processS1Slatepack complete
    def test_processS1Slatepack_completed(self):
        update = MagicMock()
        update.message.chat.id = 0
        update.message.from_user.id = 0

        context = MagicMock()
        context.bot.send_message.return_value = True

        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        slate = {
            'ver': '4:3',
            'id': tx_id,
            'sta': 'S1',
            'amt': 320000
        }

        P1 = patch('slateboy.providers.WalletProvider.isReady',
                   return_value=(True, None))

        P2 = patch('slateboy.personality.BlankPersonality.shouldSeeEULA',
                   return_value=(False, 'very eula', 'eula_v1'))

        P3 = patch('slateboy.personality.BlankPersonality.canDeposit',
                   return_value=(True, None, True, 320000))

        P4 = patch('slateboy.providers.WalletProvider.receive',
                   return_value=(True, None, 'slatepack', 'tx_id'))

        reason = 'no way Jose'
        P5 = patch('slateboy.personality.BlankPersonality.assignDepositTx',
                   return_value=(True, None, 'instructions', 'msg'))

        P6 = patch('slateboy.slateboy.SlateBoy.completeFinancialOperation',
                   return_value=(True))

        with P1, P2, P3, P4, P5, P6:
            shall_continue = self.slateboy.processS1Slatepack(update, context, slate, tx_id)
            assert shall_continue

    # shouldFinalizeQueryMethod stops it
    def test_processSlatepack_shouldFinalizeQueryMethod(self):
        chat_id = 0
        user_id = 1

        update = MagicMock()
        update.message.chat.id = chat_id
        update.message.from_user.id = user_id

        context = MagicMock()
        context.bot.send_message.return_value = True

        reason = 'no way Jose'
        def shouldFinalizeQueryMethod(update, context, tx_id):
            should_finalize = False
            return should_finalize, reason

        def shouldFinalizeQueryMethodNoReason(update, context, tx_id):
            should_finalize = False
            return should_finalize, None

        def finalizedTxMethod(update, context, tx_id):
            success = True
            msg = ''
            return success, None, msg

        slatepack = 'slatepack'
        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        msg_slatepack_rejected = 'rejected'
        msg_slatepack_finalized = 'finalized'

        shall_continue = self.slateboy.processSlatepack(
            update,
            context,
            slatepack,
            tx_id,
            shouldFinalizeQueryMethod,
            finalizedTxMethod,
            msg_slatepack_rejected,
            msg_slatepack_finalized)

        context.bot.send_message.assert_called_with(chat_id=user_id, text=reason)
        assert shall_continue == False

        shall_continue = self.slateboy.processSlatepack(
            update,
            context,
            slatepack,
            tx_id,
            shouldFinalizeQueryMethodNoReason,
            finalizedTxMethod,
            msg_slatepack_rejected,
            msg_slatepack_finalized)

        expected = t(msg_slatepack_rejected)
        context.bot.send_message.assert_called_with(
            chat_id=user_id, text=expected)
        assert shall_continue == False

    # wallet stops it
    def test_processSlatepack_finalize_fails(self):
        chat_id = 0
        user_id = 1

        update = MagicMock()
        update.message.chat.id = chat_id
        update.message.from_user.id = user_id

        context = MagicMock()
        context.bot.send_message.return_value = True

        def shouldFinalizeQueryMethod(update, context, tx_id):
            should_finalize = True
            reason = None
            return should_finalize, reason

        reason = 'no way Jose'
        msg = 'mmomm'
        def finalizedTxMethod(update, context, tx_id):
            success = False
            return success, reason, msg

        def finalizedTxMethodOK(update, context, tx_id):
            success = True
            return success, reason, msg

        def finalizedTxMethodOKMysterious(update, context, tx_id):
            success = True
            return success, reason, None

        slatepack = 'slatepack'
        tx_id = '0436430c-2b02-624c-2032-570501212b00'
        msg_slatepack_rejected = 'rejected'
        msg_slatepack_finalized = 'finalized'

        wallet_reason = 'wallet ricked'
        P1 = patch('slateboy.providers.WalletProvider.finalize',
                   return_value=(False, wallet_reason, None))

        with P1:
            shall_continue = self.slateboy.processSlatepack(
                update,
                context,
                slatepack,
                tx_id,
                shouldFinalizeQueryMethod,
                finalizedTxMethod,
                msg_slatepack_rejected,
                msg_slatepack_finalized)

            context.bot.send_message.assert_called_with(
                chat_id=user_id, text=wallet_reason)
            assert shall_continue == False

        P2 = patch('slateboy.providers.WalletProvider.finalize',
                   return_value=(True, None, 'response'))

        with P2:
            shall_continue = self.slateboy.processSlatepack(
                update,
                context,
                slatepack,
                tx_id,
                shouldFinalizeQueryMethod,
                finalizedTxMethod,
                msg_slatepack_rejected,
                msg_slatepack_finalized)

            context.bot.send_message.assert_called_with(
                chat_id=user_id, text=reason)
            assert shall_continue == False

            shall_continue = self.slateboy.processSlatepack(
                update,
                context,
                slatepack,
                tx_id,
                shouldFinalizeQueryMethod,
                finalizedTxMethodOK,
                msg_slatepack_rejected,
                msg_slatepack_finalized)

            context.bot.send_message.assert_called_with(
                chat_id=user_id, text=msg)
            assert shall_continue == False

            shall_continue = self.slateboy.processSlatepack(
                update,
                context,
                slatepack,
                tx_id,
                shouldFinalizeQueryMethod,
                finalizedTxMethodOKMysterious,
                msg_slatepack_rejected,
                msg_slatepack_finalized)

            expected = t(msg_slatepack_finalized)
            context.bot.send_message.assert_called_with(
                chat_id=user_id, text=expected)
            assert shall_continue == False

# TODO test validateFinancialOperation
# TODO test completeFinancialOperation
