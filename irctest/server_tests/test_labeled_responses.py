"""
<https://ircv3.net/specs/extensions/labeled-response.html>
"""

from irctest import cases
from irctest.basecontrollers import NotImplementedByController

class LabeledResponsesTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledPrivmsgResponsesToMultipleClients(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(2)
        self.connectClient('carl', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(3)
        self.connectClient('alice', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(4)

        self.sendLine(1, '@draft/label=12345 PRIVMSG bar,carl,alice :hi')
        m = self.getMessage(1)
        m2 = self.getMessage(2)
        m3 = self.getMessage(3)
        m4 = self.getMessage(4)

        # ensure the label isn't sent to recipients
        self.assertMessageEqual(m2, command='PRIVMSG', fail_msg='No PRIVMSG received by target 1 after sending one out')
        self.assertNotIn('draft/label', m2.tags, m2, fail_msg="When sending a PRIVMSG with a label, the target users shouldn't receive the label (only the sending user should): {msg}")
        self.assertMessageEqual(m3, command='PRIVMSG', fail_msg='No PRIVMSG received by target 1 after sending one out')
        self.assertNotIn('draft/label', m3.tags, m3, fail_msg="When sending a PRIVMSG with a label, the target users shouldn't receive the label (only the sending user should): {msg}")
        self.assertMessageEqual(m4, command='PRIVMSG', fail_msg='No PRIVMSG received by target 1 after sending one out')
        self.assertNotIn('draft/label', m4.tags, m4, fail_msg="When sending a PRIVMSG with a label, the target users shouldn't receive the label (only the sending user should): {msg}")

        self.assertMessageEqual(m, command='BATCH', fail_msg='No BATCH echo received after sending one out')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledPrivmsgResponsesToClient(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(2)

        self.sendLine(1, '@draft/label=12345 PRIVMSG bar :hi')
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageEqual(m2, command='PRIVMSG', fail_msg='No PRIVMSG received by the target after sending one out')
        self.assertNotIn('draft/label', m2.tags, m2, fail_msg="When sending a PRIVMSG with a label, the target user shouldn't receive the label (only the sending user should): {msg}")

        self.assertMessageEqual(m, command='PRIVMSG', fail_msg='No PRIVMSG echo received after sending one out')
        self.assertIn('draft/label', m.tags, m, fail_msg="When sending a PRIVMSG with a label, the echo'd message didn't contain the label at all: {msg}")
        self.assertEqual(m.tags['draft/label'], '12345', m, fail_msg="Echo'd PRIVMSG to a client did not contain the same label we sent it with(should be '12345'): {msg}")

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledPrivmsgResponsesToChannel(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(2)

        # join channels
        self.sendLine(1, 'JOIN #test')
        self.getMessages(1)
        self.sendLine(2, 'JOIN #test')
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, '@draft/label=12345;+draft/reply=123;+draft/react=l😃l PRIVMSG #test :hi')
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageEqual(mt, command='PRIVMSG', fail_msg='No PRIVMSG received by the target after sending one out')
        self.assertNotIn('draft/label', mt.tags, mt, fail_msg="When sending a PRIVMSG with a label, the target user shouldn't receive the label (only the sending user should): {msg}")

        # ensure sender correctly receives msg
        self.assertMessageEqual(ms, command='PRIVMSG', fail_msg="Got a message back that wasn't a PRIVMSG")
        self.assertIn('draft/label', ms.tags, ms, fail_msg="When sending a PRIVMSG with a label, the source user should receive the label but didn't: {msg}")
        self.assertEqual(ms.tags['draft/label'], '12345', ms, fail_msg="Echo'd label doesn't match the label we sent (should be '12345'): {msg}")

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledPrivmsgResponsesToSelf(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)

        self.sendLine(1, '@draft/label=12345 PRIVMSG foo :hi')
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)

        number_of_labels = 0
        for m in [m1, m2]:
            self.assertMessageEqual(m, command='PRIVMSG', fail_msg="Got a message back that wasn't a PRIVMSG")
            if 'draft/label' in m.tags:
                number_of_labels += 1
                self.assertEqual(m.tags['draft/label'], '12345', m, fail_msg="Echo'd label doesn't match the label we sent (should be '12345'): {msg}")
        
        self.assertEqual(number_of_labels, 1, m1, fail_msg="When sending a PRIVMSG to self with echo-message, we only expect one message to contain the label. Instead, {} messages had the label".format(number_of_labels))

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledNoticeResponsesToClient(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(2)

        self.sendLine(1, '@draft/label=12345 NOTICE bar :hi')
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageEqual(m2, command='NOTICE', fail_msg='No NOTICE received by the target after sending one out')
        self.assertNotIn('draft/label', m2.tags, m2, fail_msg="When sending a NOTICE with a label, the target user shouldn't receive the label (only the sending user should): {msg}")

        self.assertMessageEqual(m, command='NOTICE', fail_msg='No NOTICE echo received after sending one out')
        self.assertIn('draft/label', m.tags, m, fail_msg="When sending a NOTICE with a label, the echo'd message didn't contain the label at all: {msg}")
        self.assertEqual(m.tags['draft/label'], '12345', m, fail_msg="Echo'd NOTICE to a client did not contain the same label we sent it with(should be '12345'): {msg}")

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledNoticeResponsesToChannel(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(2)

        # join channels
        self.sendLine(1, 'JOIN #test')
        self.getMessages(1)
        self.sendLine(2, 'JOIN #test')
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, '@draft/label=12345;+draft/reply=123;+draft/react=l😃l NOTICE #test :hi')
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageEqual(mt, command='NOTICE', fail_msg='No NOTICE received by the target after sending one out')
        self.assertNotIn('draft/label', mt.tags, mt, fail_msg="When sending a NOTICE with a label, the target user shouldn't receive the label (only the sending user should): {msg}")

        # ensure sender correctly receives msg
        self.assertMessageEqual(ms, command='NOTICE', fail_msg="Got a message back that wasn't a NOTICE")
        self.assertIn('draft/label', ms.tags, ms, fail_msg="When sending a NOTICE with a label, the source user should receive the label but didn't: {msg}")
        self.assertEqual(ms.tags['draft/label'], '12345', ms, fail_msg="Echo'd label doesn't match the label we sent (should be '12345'): {msg}")

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledNoticeResponsesToSelf(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response'], skip_if_cap_nak=True)
        self.getMessages(1)

        self.sendLine(1, '@draft/label=12345 NOTICE foo :hi')
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)

        number_of_labels = 0
        for m in [m1, m2]:
            self.assertMessageEqual(m, command='NOTICE', fail_msg="Got a message back that wasn't a NOTICE")
            if 'draft/label' in m.tags:
                number_of_labels += 1
                self.assertEqual(m.tags['draft/label'], '12345', m, fail_msg="Echo'd label doesn't match the label we sent (should be '12345'): {msg}")
        
        self.assertEqual(number_of_labels, 1, m1, fail_msg="When sending a NOTICE to self with echo-message, we only expect one message to contain the label. Instead, {} messages had the label".format(number_of_labels))

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledTagMsgResponsesToClient(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response', 'draft/message-tags-0.2'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response', 'draft/message-tags-0.2'], skip_if_cap_nak=True)
        self.getMessages(2)

        self.sendLine(1, '@draft/label=12345;+draft/reply=123;+draft/react=l😃l TAGMSG bar')
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageEqual(m2, command='TAGMSG', fail_msg='No TAGMSG received by the target after sending one out')
        self.assertNotIn('draft/label', m2.tags, m2, fail_msg="When sending a TAGMSG with a label, the target user shouldn't receive the label (only the sending user should): {msg}")
        self.assertIn('+draft/reply', m2.tags, m2, fail_msg="Reply tag wasn't present on the target user's TAGMSG: {msg}")
        self.assertEqual(m2.tags['+draft/reply'], '123', m2, fail_msg="Reply tag wasn't the same on the target user's TAGMSG: {msg}")
        self.assertIn('+draft/react', m2.tags, m2, fail_msg="React tag wasn't present on the target user's TAGMSG: {msg}")
        self.assertEqual(m2.tags['+draft/react'], 'l😃l', m2, fail_msg="React tag wasn't the same on the target user's TAGMSG: {msg}")

        self.assertMessageEqual(m, command='TAGMSG', fail_msg='No TAGMSG echo received after sending one out')
        self.assertIn('draft/label', m.tags, m, fail_msg="When sending a TAGMSG with a label, the echo'd message didn't contain the label at all: {msg}")
        self.assertEqual(m.tags['draft/label'], '12345', m, fail_msg="Echo'd TAGMSG to a client did not contain the same label we sent it with(should be '12345'): {msg}")
        self.assertIn('+draft/reply', m.tags, m, fail_msg="Reply tag wasn't present on the source user's TAGMSG: {msg}")
        self.assertEqual(m2.tags['+draft/reply'], '123', m, fail_msg="Reply tag wasn't the same on the source user's TAGMSG: {msg}")
        self.assertIn('+draft/react', m.tags, m, fail_msg="React tag wasn't present on the source user's TAGMSG: {msg}")
        self.assertEqual(m2.tags['+draft/react'], 'l😃l', m, fail_msg="React tag wasn't the same on the source user's TAGMSG: {msg}")

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledTagMsgResponsesToChannel(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response', 'draft/message-tags-0.2'], skip_if_cap_nak=True)
        self.getMessages(1)
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response', 'draft/message-tags-0.2'], skip_if_cap_nak=True)
        self.getMessages(2)

        # join channels
        self.sendLine(1, 'JOIN #test')
        self.getMessages(1)
        self.sendLine(2, 'JOIN #test')
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, '@draft/label=12345;+draft/reply=123;+draft/react=l😃l TAGMSG #test')
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageEqual(mt, command='TAGMSG', fail_msg='No TAGMSG received by the target after sending one out')
        self.assertNotIn('draft/label', mt.tags, mt, fail_msg="When sending a TAGMSG with a label, the target user shouldn't receive the label (only the sending user should): {msg}")

        # ensure sender correctly receives msg
        self.assertMessageEqual(ms, command='TAGMSG', fail_msg="Got a message back that wasn't a TAGMSG")
        self.assertIn('draft/label', ms.tags, ms, fail_msg="When sending a TAGMSG with a label, the source user should receive the label but didn't: {msg}")
        self.assertEqual(ms.tags['draft/label'], '12345', ms, fail_msg="Echo'd label doesn't match the label we sent (should be '12345'): {msg}")

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testLabeledTagMsgResponsesToSelf(self):
        self.connectClient('foo', capabilities=['batch', 'echo-message', 'draft/labeled-response', 'draft/message-tags-0.2'], skip_if_cap_nak=True)
        self.getMessages(1)

        self.sendLine(1, '@draft/label=12345;+draft/reply=123;+draft/react=l😃l TAGMSG foo')
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)

        number_of_labels = 0
        for m in [m1, m2]:
            self.assertMessageEqual(m, command='TAGMSG', fail_msg="Got a message back that wasn't a TAGMSG")
            if 'draft/label' in m.tags:
                number_of_labels += 1
                self.assertEqual(m.tags['draft/label'], '12345', m, fail_msg="Echo'd label doesn't match the label we sent (should be '12345'): {msg}")

        self.assertEqual(number_of_labels, 1, m1, fail_msg="When sending a TAGMSG to self with echo-message, we only expect one message to contain the label. Instead, {} messages had the label".format(number_of_labels))
