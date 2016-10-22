# dwarf fortress raw indexer

import yaml

import rawparse

df_raw_types = {
    'BODY' : {'BODY'},
    'BODY_DETAIL_PLAN' : {'BODY_DETAIL_PLAN'},
    'BUILDING' : {'BUILDING'},
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

class Robject(object):
    def __init__(self, content, ns = None, verbosity = 0):
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
        else:
            self.ident = tags[0]
            if verbosity >= 0 and  len(tags) > 1:
                print('INVALID: multiple identifiers in token {:s}'
                      .format(repr(token)))

        self._comments = []
        self._tokens = []
        self.tags = []   
        tags_i = {}
        i = 0
        for comment, token, tokname, tags in content[1:]:
            self._comments.append(comment)
            if token:
                self._tokens.append(token)
                self.tags.append((tokname, tags))
                if tokname in tags_i:
                    tags_i[tokname].append(i)
                else:
                    tags_i[tokname] = [i]
            i += 1
        self.tag_idx = {k : tuple(tags_i[k]) for k in tags_i}

class Rnamespace(object):
    def __init__(self, tup, verbosity = 0):
        name, objc, objt, content = tup
        self.name = name
        self.rawtype = objt
        self._objc = objc
        if objt in df_raw_types:
            self.subtypes = df_raw_types[objt]
        else:
            self.subtypes = {}
            if verbosity >= 0:
                print('INVALID: unrecognized raw object type {:s}'
                      .format(repr(objt)))

        self.items = []
        current = []
        for x in content:
            _, _, tokname, _ = x
            if current and tokname in self.subtypes:
                self.items.append(Robject(current, ns=self, verbosity=verbosity))
                current = []
            current.append(x)
        if current:
            self.items.append(Robject(current, ns=self, verbosity=verbosity))


if __name__ == '__main__':
    import sys

    tup = rawparse.readraw(sys.argv[1], verbosity=1)
    ns = Rnamespace(tup)

    print(yaml.dump({'ns' : ns}))
