import codecs
import collections

ebayCatSet=set()
ebayCatidIdxMap={}
ebayCatidNameMap={}

for line in codecs.open('targetIDs', 'r', 'utf-8').readlines():
    catname, catid = line.strip().split('\t')
    ebayCatSet.add(catid)
    ebayCatidNameMap[catid]=catname

ebayCatidIdxMap = { catid:idx for (idx, catid) in enumerate(list(ebayCatSet))  }
outTrainFile=codecs.open('train.tsv', 'w', 'utf-8')
outTestFile = codecs.open('test.tsv', 'w', 'utf-8')
outCatIdFile = codecs.open('categoryId.tsv', 'w', 'utf-8')

outTrainFile.write('####Title, eBayCatId, CatIndex\n')
for line in codecs.open('TrainPairs', 'r', 'utf'):
    title, catid = line.strip().split('\t')
    outTrainFile.write( '\t'.join([title, catid, str(ebayCatidIdxMap[catid])]) + '\n' )

outTestFile.write('####Title, eBayCatId, CatIndex\n')
for line in codecs.open('EvalPairs', 'r', 'utf'):
    title, catid = line.strip().split('\t')
    outTestFile.write( '\t'.join([title, catid, str(ebayCatidIdxMap[catid])]) + '\n' )


outCatIdFile.write('####eBayCatName, eBayCatId, CatIndex\n')
for line in codecs.open('targetIDs', 'r', 'utf'):
    catname, catid = line.strip().split('\t')
    outCatIdFile.write( '\t'.join([catname, catid, str(ebayCatidIdxMap[catid])]) + '\n' )

outTrainFile.close()
outTestFile.close()
outCatIdFile.close()