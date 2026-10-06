"""Build-only validation. Read lemmas and synonym links, never definitions."""
from pathlib import Path
import collections, hashlib, json, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
POS = {'n.': 'n', 'v.': 'v', 'adj.': 'a', 'adv.': 'r'}

class WordNetGuard:
    def __init__(self, download=False):
        self.meta = json.loads((ROOT/'vocabulary/data/wordnet-source.json').read_text())
        path = ROOT/'build/vocabulary-research/nltk__nltk_data/wordnet.zip'
        if not path.exists() and download:
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(self.meta['url'], path)
        if not path.exists():
            raise ValueError('Run prepare_expansion.py --download to fetch pinned WordNet')
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.meta['sha256']:
            raise ValueError('WordNet checksum mismatch')
        self.lemmas = collections.defaultdict(set)
        links = collections.defaultdict(set)
        with zipfile.ZipFile(path) as archive:
            for name in ['noun', 'verb', 'adj', 'adv']:
                for line in archive.read('wordnet/data.'+name).decode('utf-8').splitlines():
                    if not line or not line[0].isdigit(): continue
                    fields = line.split('|', 1)[0].split()
                    pos = 'a' if fields[2] == 's' else fields[2]
                    synset = (pos, fields[0]); count = int(fields[3], 16)
                    for i in range(count):
                        lemma = fields[4+2*i].replace('_', ' ')
                        for marker in ['(a)', '(p)', '(ip)']: lemma = lemma.removesuffix(marker)
                        self.lemmas[(pos, lemma)].add(synset)
                    cursor = 4+2*count
                    for i in range(int(fields[cursor])):
                        symbol, offset, target_pos, _ = fields[cursor+1+4*i:cursor+5+4*i]
                        if pos == 'a' and symbol == '&': links[synset].add(('a', offset))
        self.links = links

    def synsets(self, word, pos):
        found = self.lemmas.get((POS.get(pos), word), set())
        return found | {target for key in found for target in self.links.get(key, ())}

    def related(self, word, pos, originals):
        candidate = self.synsets(word, pos)
        if not candidate: return False
        return any(candidate & self.synsets(base, p) for base, p in originals if p == pos)
