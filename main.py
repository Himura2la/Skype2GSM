# -*- coding: utf-8 -*-

import Skype4Py
import SIM900

skype = Skype4Py.Skype()
try:
    skype.Attach()
    print "Connected to Skype as " + skype.CurrentUserHandle
except Exception, e:
    print "Failed to connect to Skype :", e
    exit()


def answer(question):
    try:
        command = question.encode()
    except UnicodeEncodeError:  # Input is in Unicode
        if question == u"Балланс":
            return s.safe(s.ballance)
        elif question == u"СМС":
            return s.safe(s.read_SMS)
        elif question.find(u"СМС") == 0:
            _, number, text = question.split(",")
            number, text = number.strip(), text.strip()
            try:
                text = text.encode()
                s.safe(s.SMS, number, text)
                s.safe(s.get_ret, 5)
                return u"Сделано!" if s.OK else u"Неудача: " + s.r
            except UnicodeEncodeError:
                return u"Сорян, юникод пока не поддерживается. Можешь сам дописать https://github.com/Himura2la/Skype2GSM"
    else:   # Input is in ASCII
        if command == "AT":
            s.AT(safe=True)
            return u"Нарм ^_^" if s.OK else u"Чот не ((\n" + s.r

        s.AT(command, safe=True)

    return s.r


def on_call(call, status):
    global waiting4call
    if status == Skype4Py.clsRinging and \
            call.Type in {Skype4Py.cltIncomingP2P, Skype4Py.cltIncomingPSTN} and waiting4call:
        print 'Incoming call from:', call.PartnerHandle, "(" + call.PartnerDisplayName + ")"
        try:
            call.Answer()
            waiting4call = False
        except Exception, e:
            print "Failed to answer --", e

    elif status == Skype4Py.clsInProgress:
        print "Talking..."

    elif status in {Skype4Py.clsFailed, Skype4Py.clsFinished, Skype4Py.clsMissed,
                    Skype4Py.clsRefused, Skype4Py.clsBusy, Skype4Py.clsCancelled}:
        print 'Call', status.lower()
        waiting4call = True

skype.OnCallStatus = on_call


def on_message(message, status):
    if status == Skype4Py.cmsReceived and message.Type == Skype4Py.cmeSaid:
        print "[" + str(message.Datetime) + "]", message.FromHandle + ":", message.Body
        message.Chat.SendMessage(answer(message.Body))

    if status == Skype4Py.cmsSent and message.Type == Skype4Py.cmeSaid:
        print "[" + str(message.Datetime) + "] Me:", message.Body

skype.OnMessageStatus = on_message

s = SIM900.SIM900()
if s.AT():
    s.AT("GMM")
    print "Connected to " + s.r
else:
    print "Failed to connect to SIM900"
    exit()


def check_incoming(data):
    if data.find('+CMTI: "SM"') >= 0:  # New SMS
        n = data.split(",")[1]
        s.read_SMS(n)
        # TODO: Send to Skype


waiting4call = True
s.listening = True
while True:
    if s.listening:
        if s.get_ret(0.1, True):
            data = ''.join(s.ret)
            print "SIM900:", data
            s.listening = False
            check_incoming(data)
            s.listening = True



