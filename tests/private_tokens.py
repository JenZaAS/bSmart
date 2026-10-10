"""Shared SHA-256 digests for private deployment tokens.

The plaintext is not stored. Add a term with:

    python -c "import hashlib; print(hashlib.sha256('the-token'.lower().encode()).hexdigest())"

Hash the lowercased token or host-path prefix. See bSmart_Protocols/protocols.md.
"""

from __future__ import annotations

import hashlib
import re

PRIVATE_TOKEN_DIGESTS = frozenset(
    {
        "03105fee68fd9c2fa027e85bd716ff1eb1eff01aa258bbad02d358b0c6e5c880",
        "0478721f1106c2a631a90181bac7efc77767a3903eb9220687bff8a14e940fa7",
        "04fb9bbf7e86517c4967a2415b070ea33d462e2a06f9e8804ec00ec6b2ce4673",
        "0861e3c581e97eafe0c265792663d176be46b8b80d6a8ea8f57275279fb9c01a",
        "09a43f0790db91f0ca6e57ba25cbf1851b0699e1ad6c9c540dd4636e010d73cf",
        "12178f06446af3c474b6f98b6b94d7fb846abea3689f3fca74f0586b00d73a92",
        "186cf774c97b60a1c106ef718d10970a6a06e06bef89553d9ae65d938a886eae",
        "1d43cfed6bbe6dd9919678dea66a37b1576a9890cf5142a7e0d3eddf57f1e123",
        "2596620b7eb36fc3b444529e8269c1ecb05c34dff4d7f5c274fd1cb0bbcdc1b9",
        "26733044d952d0664bc37101140fcfc35ba9507263e93574c99d245a19459aa7",
        "321d3adbf89f8f1c4670ab6dff3c78a6e24b6c613db20b6a0b408750b3e64e44",
        "3f1238dcd99470917dceb70358769c869ffd214e6ff3d91410dffedbedbbdfaa",
        "41ef1aa30fe731fe99c1ea6e1320b3ec403e7fdd4628846f98c4f44fb0587d16",
        "48808b5a682452bae5ba05796e28142745e4244f5c0252a1d17f4d51218ffbbb",
        "4d62a136633602581cbfcce776811997406d0761c1c2959d90a048166cb7167f",
        "543ab4cf9dc73fe57d2191af5de8c3e345ade5cb81baa903b21a0095dc602fb7",
        "591b66b11758731f2d661ed864bab0ee82ad13ec6bb99c9abc9444bc91f647d6",
        "898e7babea371232f58d7b51e21383b5f4cf3032c6fe593d5acc6b7b7f81e4d5",
        "8e016391c88c77d6773deab343b91f53bb64bfbc9ca18101844cb84c3d01e561",
        "9042ba4bfd8c94f52369b20949cddfa87a1790dcaca65c7aed393f09975655b4",
        "9c8c14c1218f59b60b786a628f99e8cd7a69dfb3013a6f8d8cb0eb66520fb5ac",
        "9dcdeba17f5bde74b33beddd7522de54bca938e3de398638f0518f9604c5142b",
        "a519dd414c8d372fbfa5b338b66a9851e25add57a1a476c52ca9de0c3bd4b1fc",
        "a5790b06f63b7c1646f0de34b44fc108377a02fb07aa60b83aaff44deed06398",
        "a9ff1f544d15381f8078d4587648c17dd8fbc7e7747c336b5b9176d2c5e93dc6",
        "ab3e0a9b97b1141e1a723f92fca09fd915df8f0bf33a58b80c4a5ac47412f413",
        "ad913ab181d0ea36a03369a12ddcc7b072cb0a26ea41c496ad3f89f962afa84f",
        "be98fcf9606acdd720a971d216e52a0be23f2c0d9585b63eacf4293eb2047bc0",
        "c87f42bd454c031b875b76c76b0412feb4649fe67a17cc9bde2c2f31a74fbaf4",
    }
)

WORD_RE = re.compile(r"[a-z0-9]+")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
PATH_RE = re.compile(r"/[a-z0-9._-]+(?:/[a-z0-9._-]+)*")


def token_candidates(text: str):
    lower = text.lower()
    words = WORD_RE.findall(lower)
    yield from words
    for left, right in zip(words, words[1:]):
        yield left + right
    for match in TOKEN_RE.finditer(lower):
        token = match.group(0)
        yield token
        collapsed = token.replace("-", "").replace("_", "")
        if collapsed != token:
            yield collapsed
    for match in PATH_RE.finditer(lower):
        parts = match.group(0).split("/")
        acc = ""
        for part in parts[1:]:
            acc += "/" + part
            yield acc


def private_digest_hits(text: str) -> list[str]:
    found = set()
    for line in text.splitlines():
        seen = set()
        for cand in token_candidates(line):
            if cand in seen:
                continue
            seen.add(cand)
            digest = hashlib.sha256(cand.encode("utf-8")).hexdigest()
            if digest in PRIVATE_TOKEN_DIGESTS:
                found.add(digest)
    return sorted(found)
