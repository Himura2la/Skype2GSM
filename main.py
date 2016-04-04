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
    question = question.strip()
    try:
        command = question.encode()
    except UnicodeEncodeError:  # Input is in Unicode
        if question == u"Баланс":
            return s.ballance()
        elif question == u"СМС":
            SMSki = s.read_SMS()
            return "\r\n".join(SMSki) if SMSki else u"Эмпти ^_^"
        elif question == u"Удаляй":
            return u"Готово." if s.del_SMS(SIM900.scopeReadAndSent) else u"Блин..\r\n" + s.cmd + u" -> " + s.r
        elif question.find(u"СМС") == 0:
            _, number, text = question.split("  ")  # Two spaces is a non-sense for SMS :)
            number, text = number.strip(), text.strip()
            try:
                text = text.encode()
                mr = s.SMS(number, text)
                return u"Сделано! MR:" + str(mr) if mr else u"Неудача Т_Т\r\n" + s.cmd + u" -> " + s.r
            except UnicodeEncodeError:
                return u"Сорян, юникод пока не поддерживается. Надо писать латиницей. " + \
                       u"Можешь сам дописать https://github.com/Himura2la/Skype2GSM"
    else:  # Input is in ASCII
        wait_keyword = "wait"
        if command == "AT":
            s.AT()
            return u"Нарм ^_^" if s.OK else u"Чот не ((\r\n" + s.r
        elif command.find(wait_keyword) >= 0:
            try:
                time = int(command[command.find(wait_keyword) + len(wait_keyword)])  # Can add a digit in seconds
                command = command.replace(wait_keyword + str(time), "").strip()
            except (IndexError, ValueError):
                time = 1
                command = command.replace(wait_keyword, "").strip()
            s.AT(command, wait_for_data=time)
        else:
            s.AT(command)
        return s.r

    if question.lower().find(u"привет") >= 0 or \
       question.lower().find(u"hello") >= 0 or \
       question.lower().find(u"hi") >= 0:
        return "Привет, сейчас на данном аккаунте настроена связь с GSM сетью. " + \
               "Вот этот проект: https://github.com/Himura2la/Skype2GSM \r\n\r\n" + \
               "Команды бывают на русском и на нерусском. Команды на русском делают всё сразу и выводят красииво. " + \
               "Команды на нерусском интерпретируются как AT команды, и выхлоп с них почти необработанный. \r\n\r\n" + \
               "Поддерживаются смски: Можно прочитать все входящие командой 'СМС', отправить смску той же командой, " +\
               "но дополненной ЧЕРЕЗ ДВА (или более) ПРОБЕЛА номером и ЧЕРЕЗ ДВА (или более) ПРОБЕЛА текстом " + \
               "(в котором нет двоыных пробелов). Удалить прочитанные, можно командой 'Удаляй'.\r\n\r\n" + \
               "А еще, поддерживается запрос баланса. Надо написать 'Баланс'. Про ручное управление " + \
               "расскажет команда 'Валяй'. Наслаждайтесь! (номер этого чуда записан на симке, читать AT-командами)"

    elif question.lower().find(u"валяй") >= 0:
        return "\r\nПо поводу ручных команд -- " + \
               "там короче 'AT+' сам подставляется слева, так что надо писать не 'AT+CPAS', а просто 'CPAS'. " + \
               "А еще, некоторые команды могуют выполняться долго (например, 'CSPN?'): в этом случае, нужно " + \
               "куда-нибудь в запрос (либо сначала либо в конце) добавить слово 'wait'. Тогда он будет ждать " + \
               "1 секунду прежде чем вернуть ответ. Если надо еще больше, после 'wait' без пробела " + \
               "можно поставить ОДНУ цифру. Таким образом, правильый способ узнать оператора -- 'COPS? wait' " + \
               " ну или 'wait3 CSPN?', если за секунду не успевает (а вообще, 'COPS?'). \r\n\r\n" + \
               "Наслаждайтесь! Фильтра на AT командах нету, просьба ничего лишнего не трогать. Вот тебе ссылочка. " + \
               "http://we.easyelectronics.ru/part/gsm-gprs-modul-sim900-chast-vtoraya.html"

    return u"Ты втираешь мне какую-то дичь!"


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
        response = s.safe(answer, message.Body)
        message.Chat.SendMessage(response)

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
        s.read_SMS(n, leave_unread=True)
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
