# dwarf fortress raw indexer

import os
import traceback

# It turns out saving / loading the index object as YAML is 10x slower
# than just parsing all the files...

# def _importyaml():
#     from yaml import load, dump
#     try:
#         from yaml import CLoader as Loader, CDumper as Dumper
#     except ImportError:
#         from yaml import Loader, Dumper
#     def yload(stream):
#         return load(stream, Loader=Loader)
#     def ydump(data, stream):
#         return dump(data, stream, Dumper=Dumper)
#     return yload, ydump
# yload, ydump = _importyaml()

import rawparse

df_raw_types = {
    'BODY' : {'BODY'},
    'BODY_DETAIL_PLAN' : {'BODY_DETAIL_PLAN'},
    'BUILDING' : {'BUILDING_WORKSHOP'},
    'CREATURE' : {'CREATURE'},
    'CREATURE_VARIATION' : {'CREATURE_VARIATION'},
    'DESCRIPTOR_COLOR' : {'COLOR'},
    'DESCRIPTOR_PATTERN' : {'COLOR_PATTERN'},
    'DESCRIPTOR_SHAPE' : {'SHAPE'},
    'ENTITY' : {'ENTITY'},
    'GRAPHICS' : {'GRAPHICS'},
    'INTERACTION' : {'INTERACTION'},
    'INORGANIC' : {'INORGANIC'},
    'ITEM' : {
        'ITEM_AMMO',
        'ITEM_ARMOR',
        'ITEM_FOOD',
        'ITEM_GLOVES',
        'ITEM_HELM',
        'ITEM_INSTRUMENT',
        'ITEM_PANTS',
        'ITEM_SHIELD',
        'ITEM_SHOES',
        'ITEM_SIEGEAMMO',
        'ITEM_TOOL',
        'ITEM_TOY',
        'ITEM_TRAPCOMP',
        'ITEM_WEAPON',
    },
    'LANGUAGE' : {'SYMBOL', 'WORD', 'TRANSLATION'},
    'MATERIAL_TEMPLATE' : {'MATERIAL_TEMPLATE'},
    'PLANT' : {'PLANT'},
    'REACTION' : {'REACTION'},
    'TISSUE_TEMPLATE' : {'TISSUE_TEMPLATE'},
}

df_raw_ns_names = {
    'BODY' : 'body',
    'BODY_DETAIL_PLAN' : 'b_detail_plan',
    'BUILDING' : 'building',
    'CREATURE' : 'creature',
    'CREATURE_VARIATION' : 'c_variation',
    'DESCRIPTOR_COLOR' : 'descriptor_color',
    'DESCRIPTOR_PATTERN' : 'descriptor_pattern',
    'DESCRIPTOR_SHAPE' : 'descriptor_shape',
    'ENTITY' : 'entity',
    'GRAPHICS' : 'graphics',
    'INTERACTION' : 'interaction',
    'INORGANIC' : 'inorganic',
    'ITEM' : 'item',
    'LANGUAGE' : 'language',
    'MATERIAL_TEMPLATE' : 'material_template',
    'PLANT' : 'plant',
    'REACTION' : 'reaction',
    'TISSUE_TEMPLATE' : 'tissue_template',
}

class Robject(object):
    def __init__(self, content, ns = None, verbosity = 0, strict = True):
        self.namespace = ns
        comment, token, tokname, tags = content[0]
        self._comment = comment
        self._token = token
        self.subtype = tokname
        if len(tags) < 1:
            self.ident = ''
            if verbosity >= 0:
                print('INVALID: no identifier in token {:s}'
                      .format(repr(token)))
            if strict:
                raise ValueError('no ident in token {:s}'
                                 .format(repr(token)))
        else:
            self.ident = tags[0]
            if len(tags) > 1:
                if verbosity >= 0:
                    print('INVALID: multiple identifiers in token {:s}'
                          .format(repr(token)))
                if strict:
                    raise ValueError('multiple idents in token {:s}'
                                     .format(repr(token)))

        self._comments = []
        self._tokens = []
        self._tags = []
        self._tagd = {}
        i = 0
        for comment, token, tokname, tags in content[1:]:
            self._comments.append(comment)
            if token:
                self._tokens.append(token)
                self._tags.append([tokname if j < 1 else tags[j-1]
                                  for j in range(len(tags)+1)])
                if tokname in self._tagd:
                    self._tagd[tokname].append(i)
                else:
                    self._tagd[tokname] = [i]
            i += 1

    def __getitem__(self, k):
        if isinstance(k, int):
            return self._tags[k]
        elif isinstance(k, str):
            return tuple(self._tags[i] for i in self._tagd[k])
        else:
            raise ValueError('key must be int or str, got {:s}'.format(repr(k)))

    def __contains__(self, k):
        if isinstance(k, str):
            return k in self._tagd
        else:
            raise ValueError('key msy be str, got {:s}'.format(repr(k)))

    def content(self):
        yield self._comment, '['+self.subtype+':'+self.ident+']', None, None
        for c, t in zip(self._comments, self._tags):
            yield c, '['+':'.join(t)+']', None, None
        for i in range(len(self._tags), len(self._comments)):
            yield self._comments[i], '', None, None

class Rnamespace(object):
    def __init__(self, tup, verbosity = 0, strict = True):
        name, objc, objt, content = tup
        if not name.startswith(df_raw_ns_names[objt]):
            if verbosity >= 0:
                print('INVALID: namespace {:s} does not start with type {:s}'
                      .format(repr(name), repr(df_raw_ns_names[objt])))
            if strict:
                raise ValueError('namespace {:s} does not start with type {:s}'
                                 .format(repr(name), repr(df_raw_ns_names[objt])))
        self.name = name
        self.rawtype = objt
        self._comment = objc
        if objt in df_raw_types:
            self.subtypes = df_raw_types[objt]
        else:
            self.subtypes = {}
            if verbosity >= 0:
                print('INVALID: unrecognized raw object type {:s}'
                      .format(repr(objt)))
            if strict:
                raise ValueError('invalid object type {:s}'
                                 .format(repr(objt)))

        self._objects = []
        self._idents = {}
        self._invalid = []
        current = []
        next_tokname = None
        i = 0
        for x in content:
            _, _, tokname, _ = x
            if next_tokname is None:
                next_tokname = tokname
            if current and tokname in self.subtypes:
                robj = Robject(current, ns=self, verbosity=verbosity)
                ident = robj.ident
                self._objects.append(robj)
                if ident and next_tokname in self.subtypes:
                    if ident in self._idents:
                        self._idents[ident].append(i)
                        if strict:
                            raise ValueError('duplicate ident {:s}'
                                             .format(repr(ident)))
                    else:
                        self._idents[ident] = [i]
                elif strict:
                    raise ValueError('unrecognized subtype {:s} for ident {:s}'
                                     .format(repr(next_tokname), repr(ident)))
                else:
                    self._invalid.append(i)
                current = []
                next_tokname = tokname
                i += 1
            current.append(x)
        if current:
            robj = Robject(current, ns=self, verbosity=verbosity)
            ident = robj.ident
            self._objects.append(robj)
            if ident and next_tokname in self.subtypes:
                if ident in self._idents:
                    self._idents[ident].append(i)
                    if strict:
                        raise ValueError('duplicate ident {:s}'
                                         .format(repr(ident)))
                else:
                    self._idents[ident] = [i]
            elif strict:
                raise ValueError('unrecognized subtype {:s} for ident {:s}'
                                 .format(repr(next_tokname), repr(ident)))
            else:
                self._invalid.append(i)
            current = []
            i += 1

    def __getitem__(self, k):
        if isinstance(k, int):
            return self._objects[k]
        elif isinstance(k, str):
            obj_indices = self._idents[k]
            if len(obj_indices) == 1:
                return self._objects[obj_indices[0]]
            else:
                return tuple(self._tags[i] for i in obj_indices)
        else:
            raise ValueError('key must be int or str, got {:s}'.format(repr(k)))

    def __contains__(self, k):
        if isinstance(k, str):
            return k in self._idents
        else:
            raise ValueError('key msy be str, got {:s}'.format(repr(k)))

    def tofile(self, fpath, verbosity = 0):
        tup = self.name, self._comment, self.rawtype, (x for robj in self._objects 
                                                       for x in robj.content())
        rawparse.writeraw(fpath, tup, verbosity=verbosity)

def is_raw_fpath(fpath):
    return fpath.endswith('.txt') and os.path.isfile(fpath)

class Rindex(object):
    def __init__(self, rawroot = None, verbosity = 0, strict = True):
        self.verbosity = verbosity
        self.strict = strict
        if rawroot is not None:
            self._create_from_root(rawroot)

    def _setup_index(self):
        # namespace index: name -> raw namespace object
        self._rns_index = {}
        # object master index: type or subtype -> raw object
        self._robj_master = {}
        # name mangling
        self._mangled_names = set()

    def _mangle_names(self):
        for k in self._robj_master:
            self._mangled_names.add(k)
            self.__dict__[k.lower()] = self._robj_master[k]

    def _add_rns(self, rns):
        name = rns.name
        if name in self._rns_index:
            if self.verbosity >= 0:
                print('duplicate namespace {:s}, ignoring'
                      .format(repr(name)))
            if self.strict:
                raise ValueError('duplicate namespace {:s}'
                                 .format(repr(name)))
        else:
            self._rns_index[name] = rns
                
    def _add_robj(self, robj):
        rawtype = robj.namespace.rawtype
        subtype = robj.subtype
        ident = robj.ident

        if subtype not in self._robj_master:
            self._robj_master[subtype] = {}
        robj_index = self._robj_master[subtype]
        if ident in robj_index:
            if self.verbosity >= 0:
                print('duplicate ident {:s} for subtype {:s}, ignoring'
                      .format(repr(ident), repr(subtype)))
            if self.strict:
                raise ValueError('duplicate ident {:s} for subtype {:s}'
                                 .format(repr(ident), repr(subtype)))
        else:
            robj_index[ident] = robj

        # special case for items
        if rawtype == 'ITEM':
            if rawtype not in self._robj_master:
                self._robj_master[rawtype] = {}
            robj_index = self._robj_master[rawtype]
            if ident in robj_index:
                if self.verbosity >= 0:
                    print('duplicate ident {:s} for rawtype {:s}, ignoring'
                          .format(repr(ident), repr(rawtype)))
                if self.strict:
                    raise ValueError('duplicate ident {:s} for rawtype {:s}'
                                     .format(repr(ident), repr(rawtype)))
            else:
                robj_index[ident] = robj

    def _create_from_root(self, rawroot):
        if not os.path.isdir(rawroot):
            raise FileNotFoundError('no raw directory {:s}'.format(repr(rawroot)))
        self.rawroot = rawroot

        self._setup_index()
        self.objects = []
        self.namespaces = []
        for fpath in filter(is_raw_fpath, 
                            (os.path.join(rawroot, fname) for fname in os.listdir(rawroot))):
            if self.verbosity >= 2:
                print('processing raw file {:s}'.format(repr(fpath)))
            rns = Rnamespace(rawparse.readraw(fpath, verbosity=self.verbosity),
                             verbosity=self.verbosity, strict=self.strict)
            self._add_rns(rns)
            self.namespaces.append(rns)

            for robj in rns:
                self._add_robj(robj)
                self.objects.append(robj)

        self._mangle_names()
        self._setup_creature_subindex()

        if self.verbosity >= 1:
            print('created index of raws at {:s}'.format(rawroot))
            print('  {:d} namespaces, {:d} typed indices, {:d} objects'
                  .format(len(self.namespaces), len(self._robj_master), len(self.objects)))

    def _setup_creature_subindex(self):
        self.creature_B = {}
        self.creature_G = {}
        self.creature_M = {}
        self.cv_G = {}
        self.cv_M = {}

        for ident in self.creature:
            robj = self.creature[ident]
            if 'APPLY_CREATURE_VARIATION' in robj:
                cv_toks = robj['APPLY_CREATURE_VARIATION']
                if (has_tag(cv_toks, 'GIANT')
                    or has_tag(cv_toks, 'ANIMAL_PERSON') or has_tag(cv_toks, 'ANIMAL_PERSON_LEGLESS')):
                    try:
                        cp_toks = robj['COPY_TAGS_FROM']
                        assert len(cp_toks) == 1
                        assert len(cp_toks[0]) == 2
                        parent_ident = cp_toks[0][1]
                    except Exception as e:
                        print('WARNING: creature variation {:s} has invalid parent'
                              .format(repr(ident)))
                        if self.strict:
                            raise e
                        else:
                            traceback.print_exc()
                        parent_ident = None

                    if has_tag(cv_toks, 'GIANT'):
                        self.creature_G[ident] = robj
                        if parent_ident is not None:
                            self.cv_G[parent_ident] = ident
                    if has_tag(cv_toks, 'ANIMAL_PERSON') or has_tag(cv_toks, 'ANIMAL_PERSON_LEGLESS'):
                        self.creature_M[ident] = robj
                        if parent_ident is not None:
                            self.cv_M[parent_ident] = ident
                    else:
                        if self.verbosity >= 1:
                            print('misc variation {:s}'.format(repr(ident)))
                else:
                    self.creature_B[ident] = robj
            else:
                if self.verbosity >= 1:
                    print('creature {:s} appears not to have gait variations'
                          .format(repr(ident)))
                self.creature_B[ident] = robj

    def todir(self, fpath):
        if not fpath.endswith(os.sep):
            fpath += os.sep
        if not os.path.isdir(fpath):
            os.mkdir(fpath)
        elif os.listdir(fpath):
            print('ERROR: output directory {:s} is not empty, aborting'
                  .format(repr(fpath)))
            return
        for ns in self.namespaces:
            ns.tofile(fpath, verbosity=self.verbosity)

def has_tag(tokens, tag):
    return any(tag in tok for tok in tokens)

# def save_ridx(ridx, fname):
#     with open(fname, 'wt') as f:
#         ydump(ridx, f)

# def load_ridx(fname):
#     with open(fname, 'rt') as f:
#         return yload(f)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        #print('Usage: {:s} <RAWDIR> [YAML]'.format(os.path.basename(__file__)))
        print('Usage: {:s} <RAWDIR> [OUTPUTDIR]'.format(os.path.basename(__file__)))
        exit(1)
    rawdir = sys.argv[1]

    ridx = Rindex(rawroot=rawdir, verbosity=2, strict=True)

    # if len(sys.argv) > 2:
    #     idxname = sys.argv[2]
    #     print('Saving raw index to {:s}'.format(idxname))
    #     save_ridx(ridx, idxname)

    if len(sys.argv) > 2:
        outname = sys.argv[2]
        print('Saving new raws to {:s}'.format(outname))
        ridx.todir(outname)
