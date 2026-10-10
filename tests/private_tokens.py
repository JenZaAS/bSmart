"""Shared SHA-256 digests for private deployment tokens.

The plaintext is not stored. Add a term with:

    python -c "import hashlib; print(hashlib.sha256('the-token'.lower().encode()).hexdigest())"

Hash the lowercased token, a joined multi-word name, or a host-path prefix.
See bSmart_Protocols/protocols.md. The digests hide terms from casual reading.
A short word can still be guessed. This is an anti-regression guard, not a secret.
"""

from __future__ import annotations

import hashlib
import re

PRIVATE_TOKEN_DIGESTS = frozenset(
    {
        "03105fee68fd9c2fa027e85bd716ff1eb1eff01aa258bbad02d358b0c6e5c880",
        "0478721f1106c2a631a90181bac7efc77767a3903eb9220687bff8a14e940fa7",
        "04fb9bbf7e86517c4967a2415b070ea33d462e2a06f9e8804ec00ec6b2ce4673",
        "0539383974d35566f9fc9dc01c9b9259990e6d54e0d13be6b77f1315a1553361",
        "0861e3c581e97eafe0c265792663d176be46b8b80d6a8ea8f57275279fb9c01a",
        "09a43f0790db91f0ca6e57ba25cbf1851b0699e1ad6c9c540dd4636e010d73cf",
        "1d378d91389a8855fd5b2f1f1d87078313736331fe621036705d2c5ee175c4e2",
        "2596620b7eb36fc3b444529e8269c1ecb05c34dff4d7f5c274fd1cb0bbcdc1b9",
        "26733044d952d0664bc37101140fcfc35ba9507263e93574c99d245a19459aa7",
        "321d3adbf89f8f1c4670ab6dff3c78a6e24b6c613db20b6a0b408750b3e64e44",
        "3f1238dcd99470917dceb70358769c869ffd214e6ff3d91410dffedbedbbdfaa",
        "41ef1aa30fe731fe99c1ea6e1320b3ec403e7fdd4628846f98c4f44fb0587d16",
        "48808b5a682452bae5ba05796e28142745e4244f5c0252a1d17f4d51218ffbbb",
        "4d62a136633602581cbfcce776811997406d0761c1c2959d90a048166cb7167f",
        "591b66b11758731f2d661ed864bab0ee82ad13ec6bb99c9abc9444bc91f647d6",
        "888a82204c7a6bc4020fe96a7e0bfda7c284ab8b5b84b7ab59bfd4601892070a",
        "898e7babea371232f58d7b51e21383b5f4cf3032c6fe593d5acc6b7b7f81e4d5",
        "9042ba4bfd8c94f52369b20949cddfa87a1790dcaca65c7aed393f09975655b4",
        "987380beccaa8b7354c2aadeadd292d2d56cc5def723040f10232b6890064a15",
        "9c8c14c1218f59b60b786a628f99e8cd7a69dfb3013a6f8d8cb0eb66520fb5ac",
        "9dcdeba17f5bde74b33beddd7522de54bca938e3de398638f0518f9604c5142b",
        "a519dd414c8d372fbfa5b338b66a9851e25add57a1a476c52ca9de0c3bd4b1fc",
        "a64d90c64962baa81e04e7dff8f04807469a8d786abab63432379411ba792120",
        "a9ff1f544d15381f8078d4587648c17dd8fbc7e7747c336b5b9176d2c5e93dc6",
        "ab3e0a9b97b1141e1a723f92fca09fd915df8f0bf33a58b80c4a5ac47412f413",
        "ad913ab181d0ea36a03369a12ddcc7b072cb0a26ea41c496ad3f89f962afa84f",
        "be98fcf9606acdd720a971d216e52a0be23f2c0d9585b63eacf4293eb2047bc0",
        "c87f42bd454c031b875b76c76b0412feb4649fe67a17cc9bde2c2f31a74fbaf4",
        "d02bf46a2a69f79a25874a0958fed83a26e7f834ce7eadf57d5414202c1a8a58",
        "f31802b2c01d51cb387fbe0396710fdea718fb00897cb8035b92fdefc93c221e",
    }
)

# Published organization login. A CamelCase split of this token is not an
# agent-name compound.
PUBLIC_COMPOUND_TOKENS = frozenset({"jenzaas"})

WORD_RE = re.compile(r"[a-z0-9]+")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
PATH_RE = re.compile(r"/[a-z0-9._-]+(?:/[a-z0-9._-]+)*")
REL_PATH_RE = re.compile(r"(?<![a-z0-9._-])[a-z0-9._-]+(?:/[a-z0-9._-]+)+")
DRIVE_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?=/)")
IDENT_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
CAMEL_PART_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def _normalize_separators(text: str) -> str:
    normalized = text.replace("\\", "/")
    return DRIVE_RE.sub("", normalized)


def _compound_prefixes(token: str):
    """Agent-name prefixes of a CamelCase or letter-plus-digit compound.

    Ordinary words are one part and yield nothing. The published organization
    login is skipped so its internal capitals are not treated as a compound.
    """
    if token.lower() in PUBLIC_COMPOUND_TOKENS:
        return
    parts = CAMEL_PART_RE.findall(token)
    if len(parts) < 2:
        return
    if not any(part[:1].isupper() or part[:1].isdigit() for part in parts[1:]):
        return
    acc = ""
    for part in parts[:-1]:
        acc += part.lower()
        if len(acc) >= 4:
            yield acc


def token_candidates(text: str):
    normalized = _normalize_separators(text)
    lower = normalized.lower()
    words = WORD_RE.findall(lower)
    yield from words
    for left, right in zip(words, words[1:]):
        yield left + right
    for first, second, third in zip(words, words[1:], words[2:]):
        yield first + second + third
    for match in TOKEN_RE.finditer(lower):
        token = match.group(0)
        yield token
        collapsed = token.replace("-", "").replace("_", "")
        if collapsed != token:
            yield collapsed
    for match in PATH_RE.finditer(lower):
        parts = [part for part in match.group(0).split("/") if part]
        acc = ""
        for part in parts:
            acc += "/" + part
            yield acc
    for match in REL_PATH_RE.finditer(lower):
        parts = [part for part in match.group(0).split("/") if part]
        acc = parts[0]
        for part in parts[1:]:
            acc += "/" + part
            yield acc
    for match in IDENT_RE.finditer(text):
        yield from _compound_prefixes(match.group(0))


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
