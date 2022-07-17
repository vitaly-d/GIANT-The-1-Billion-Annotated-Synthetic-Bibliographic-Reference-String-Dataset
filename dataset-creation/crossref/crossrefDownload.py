"""get random citeproc-json records from Crossref"""

from habanero import cn
from habanero import Crossref
import time

from tqdm import tqdm

start = time.time()

cr = Crossref()
cr.mailto = "vdaviden@wiley.com"

for i in tqdm(range(6000)):
    # get random dois (Max: 100)
    try:
        randomDois = cr.random_dois(100)
        time.sleep(0.5)  # to avoid rate limit
    except:
        print("Exception occured with random_dois on loop:", i)
        pass

    try:
        resultsCrossRefAPI = cn.content_negotiation(
            ids=randomDois, format="citeproc-json")

        # append to file
        with open(f'out/results.{i}.json', 'w') as f:
            for item in resultsCrossRefAPI:
                f.write("%s\n" % item)

        # print("Completed: ", i * 100)
    except:
        print("Exception occured with getting results on loop:", i)
        pass

    time.sleep(0.5)

end = time.time()
print("Time: ", end - start)
