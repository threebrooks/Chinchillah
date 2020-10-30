import sys
import datetime
import matplotlib.pyplot as plt

with open(sys.argv[1]) as fp:
    ogb = -1
    xs = []
    ys = []
    for line in fp.readlines():
        line = line.strip()
        els = line.split(" ")
        date = datetime.datetime.strptime(els[0], '%Y/%m/%d')
        fgb = float(els[1])
        if (ogb == -1):
            ogb = fgb
            og = ogb*0.004+1
        fg = 1 - 0.0044993*ogb + 0.0117741*fgb + 0.000275806*ogb*ogb - 0.00127169*fgb*fgb - 0.00000727999*ogb*ogb*ogb + 0.0000632929*fgb*fgb*fgb
        abv = (og-fg)*131.25
        print(str(date)+" "+str(fg)+" "+str(abv))
        xs.append(date)
        ys.append(abv)
    plt.gcf().autofmt_xdate()
    plt.plot(xs, ys)
    plt.show()
