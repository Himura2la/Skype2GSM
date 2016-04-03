import threading


def worker(num, callback):
    if num > 2:
        callback(num)
    return


def write(text):
    print text

threads = []
for i in range(5):
    t = threading.Thread(target=worker, args=(i, write,))
    threads.append(t)
    t.start()

