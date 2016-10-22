# dwarf fortress raw parser

import os
import re
import mmap

df_raw_encoding = 'cp437'

tag_body_pattern = r'[^:\]]*'
tag_pattern = re.escape(':') + tag_body_pattern
tag_re = re.compile(tag_pattern.encode(df_raw_encoding))

token_pattern = (re.escape('[')
                 + '(' + tag_body_pattern + ')' # token name
                 + '(' + tag_pattern + ')*'     # token fields
                 + re.escape(']'))
token_re = re.compile(token_pattern.encode(df_raw_encoding))

context_pattern = ('(.*?)'                      # match comment, NOT greedy
                   + '(' + token_pattern + ')') # match token
context_re = re.compile(context_pattern.encode(df_raw_encoding), flags=re.DOTALL)

rawname_pattern = r'.*?\n'
rawname_re = re.compile(rawname_pattern.encode(df_raw_encoding), flags=re.DOTALL)

crlf_pattern = '\r?\n'
crlf_re = re.compile(crlf_pattern.encode(df_raw_encoding))

# helpers

def valid(name, objdata):
    obj_comment, obj_token, obj, obj_tags = objdata
    return obj == 'OBJECT' and len(obj_tags) == 1 and name.strip() != ''

def crlf(buf):
    return crlf_re.sub('\r\n'.encode(df_raw_encoding), buf)

# parsing engine

def parse(buf):
    name_m = rawname_re.match(buf)
    if name_m:
        name = name_m.group(0)
        obj_idx = name_m.end()
    else:
        name = b''
        obj_idx = 0
    
    obj_m = context_re.match(buf, obj_idx)
    if obj_m:
        obj_comment = obj_m.group(1)
        obj_token = obj_m.group(2)
        obj = obj_m.group(3)
        content_idx = obj_m.end()
    else:        
        obj_comment = b''
        obj_token = b''
        obj = b''
        content_idx = obj_idx

    contexts = []
    lastidx = obj_idx
    for m in context_re.finditer(buf, content_idx):
        comment = m.group(1)
        token = m.group(2)
        tokname = m.group(3)
        contexts.append(
            (comment.decode(df_raw_encoding),
             token.decode(df_raw_encoding),
             tokname.decode(df_raw_encoding),
             tuple(tagm.group()[1:].decode(df_raw_encoding)
                   for tagm in tag_re.finditer(token, len(tokname)+1)))
        )
        lastidx = m.end()
    lastcomment = buf[lastidx:].decode(df_raw_encoding)
    if lastcomment != '':
        contexts.append((lastcomment, '', '', tuple()))
    
    return (name.decode(df_raw_encoding),
            (obj_comment.decode(df_raw_encoding),
             obj_token.decode(df_raw_encoding),
             obj.decode(df_raw_encoding),
             tuple(tagm.group()[1:].decode(df_raw_encoding)
                   for tagm in tag_re.finditer(obj_token, len(obj)+1))),
            contexts)

def fparse(fname):
    with open(fname, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            return parse(mm)

def readraw(fpath, verbosity = 0):
    if not os.path.isfile(fpath):
        raise FileNotFoundError('no raw file {:s}'.format(repr(fpath)))

    fname = os.path.basename(fpath)
    fname_fragments = fname.split('.')
    fname_cleaned = '.'.join(fname_fragments[:-1])
    if verbosity >= 0 and fname_fragments[-1] != 'txt':
        print('WARNING: raw file {:s} does not appear to have .txt extension'
              .format(repr(fname)))

    name, objdata, content = fparse(fpath)
    obj_comment, obj_token, obj, obj_tags = objdata

    name_cleaned = name.strip()
    name_fragments = name_cleaned.split()
    if verbosity >= 0 and len(name_fragments) != 1:
        print('WARNING: whitespace in raw filename {:s}'
              .format(repr(name_cleaned)))
    if verbosity >= 0 and name_cleaned != fname_cleaned:
        print('WARNING: raw name {:s} does not agree with filename {:s}'
              .format(repr(name_cleaned), repr(fname_cleaned)))

    if verbosity >= 0 and not valid(name, objdata):
        print('WARNING: name or object token {:s} is invalid!'
              .format(repr(obj_token)))

    if len(obj_tags) <= 0:
        obj_type = ''
        if verbosity >= 0:
            print('WARNING: object token {:s} does not have type'
                  .format(repr(obj_token)))
    else:
        obj_type = obj_tags[0]
        if verbosity >= 0 and len(obj_tags) > 1:
            print('WARNING: object token {:s} has more than one argument'
                  .format(repr(obj_token)))

    if content:
        lastcomment, lasttoken, _, _ = content[-1]
        if lasttoken == '' and lastcomment.strip() == '':
            content.pop()

    if verbosity >= 1:
        print('read {:s}, {:s}, {:d} tokens'
              .format(fname, obj_token, len(content)))

    return name_cleaned, obj_comment, obj_type, content

# complement to parse
def unparse(tup):
    name, objdata, content = tup
    obj_comment, obj_token, obj, obj_tags = objdata
    return crlf(
        (name + obj_comment + obj_token
         + ''.join((c+t for c,t,_,_ in content))).encode(df_raw_encoding)
    )

# unparse a valid result from readraw
def encoderaw(tup):
    name, objc, objt, content = tup
    return unparse(
        (name + '\n',
         (objc, '[OBJECT:'+objt+']', '', tuple()),
         content)
    )

# write valid readraw tuple to file
def writeraw(fpath, tup, verbosity = 0):
    name, objc, objt, content = tup
    fname = os.path.basename(fpath)
    if fname == '':
        fname = name + '.txt'
        fpath = os.path.join(fpath, fname)
    elif verbosity >= 0:
        fname_fragments = fname.split('.')
        fname_cleaned = '.'.join(fname_fragments[:-1])
        if fname_fragments[-1] != 'txt':
            print('WARNING: requested filename {:s} does not have .txt extension'
                  .format(repr(fname)))
        if fname_cleaned != name:
            print('WARNING: requested filename {:s} does not match raw name {:s}'
                  .format(repr(fname), repr(name)))

    # Since encoding creates the entire buffer in memory, this could have 2x overhead.
    # Probably doesn't matter.
    with open(fpath, 'wb') as f:
        f.write(encoderaw(tup))

    if verbosity >= 1:
        print('wrote {:s}, {:s}, {:d} tokens'
              .format(fname, '[OBJECT:'+objt+']', len(content)))


if __name__ == '__main__':
    import sys
    fpath = sys.argv[1]

    # test parse / unparse
    with open(fpath, 'rb') as f:
        bits = f.read()
    bits_cleaned = crlf(bits).decode(df_raw_encoding).strip()
    rawtup = fparse(fpath)
    assert unparse(rawtup).decode(df_raw_encoding).strip() == bits_cleaned
    if len(sys.argv) > 2:
        print('parse / unparse pass!')

    readtup = readraw(fpath, verbosity=1)
    name, objc, objt, content = readtup
    if len(sys.argv) > 3:
        for comment, token, tokname, tags in content:
            print(repr(comment), repr(token))

    # test readraw / encoderaw
    rawname, objdata, _ = rawtup
    if valid(rawname, objdata):
        assert encoderaw(readtup).decode(df_raw_encoding).strip() == bits_cleaned
        if len(sys.argv) > 2:
            print('readraw / encoderaw pass!')
