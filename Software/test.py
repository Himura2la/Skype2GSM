def safe(f, *args):
    print "safety on"
    r = f(*args)
    print "safety off"
    return r


def o(string, integer):
    print string + str(integer + 1)
    return "ret"


print safe(o, "work", 10)
