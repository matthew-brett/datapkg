import os
import re

class Metadata(dict):
    key_list = [
       'id',
       'name', 
       'title',
       'version',
       'license',
       'author',
       'author_email',
       'maintainer',
       'maintainer_email',
       'url',
       'download_url',
       'notes',
       'tags',
       'resources',
       'extras',
       'relationships',
       ]
    # if not specified '' will be used
    defaults = {
        'tags': [],
        'extras': {},
        # 'relationships': [],
        'resources': []
        }


class MetadataConverter(object):
    @classmethod
    def from_distutils(self, data):
        '''Convert distutils metadata to a simple metadata dictionary suitable
        for our consumption.

        @param data: a `distutils.dist.DistributionMetadata` instance
        '''
        inmeta = self._standardize_distutils(data)

        distutils_keymap = {
            'summary': 'title',
            'description': 'title',
            'long_description': 'notes',
            'keywords': 'tags',
            }
        # in case where loading from PKG-INFO - see comments in
        # _standardize_distutils
        if inmeta['summary']:
            distutils_keymap['description'] = 'notes'
        else:
            del distutils_keymap['summary']
        if inmeta['home_page']:
            inmeta['url'] = inmeta['home_page']
            del inmeta['home_page']

        newmeta = self.normalize_metadata(inmeta, distutils_keymap)
        return newmeta
    
    @classmethod
    def _standardize_distutils(self, data):
        # bit of a nightmare here since we can load either direct from setup.py
        # or from PKG-INFO
        # In PKG-INFO names from setup.py are remapped!!
        # description -> summary
        # long_description -> description (!!)
        # download_url -> Download-URL 
        # url -> Home-Page

        # Note also keywords are comma separated!
        # TODO: (?) deal with keywords/tags (may be a python list ...)
        inmeta = {}

        # python distutils/PKG-INFO attr names
        attrnames = set(data._METHOD_BASENAMES)
        # items that are not needed (generated by distutils from other values)
        attrnames.remove('fullname')
        attrnames.remove('contact_email')
        attrnames.remove('contact')

        attrnames.add('summary')
        attrnames.add('home_page')
        for attrname in attrnames:
            value = getattr(data, attrname, None) or ''
            # required values are set to UNKNOWN by distutils
            if value == 'UNKNOWN':
                value = ''
            inmeta[attrname] = unicode(value, encoding='utf8', errors='ignore') 

        return inmeta

    @classmethod
    def to_distutils(self, metadata):
        '''Convert a metadata dictionary to distutils DistributionMetadata.

        TODO: support extras (write them into notes/long_description)
        '''
        distutils_metadata = distutils.dist.DistributionMetadata()
        for key, value in metadata.items():
            # TODO: use the keymap ...
            # TODO: tags may be list not a string ...
            setkey = key
            tval = value
            if key == 'tags':
                setkey = 'keywords'
            elif key == 'title':
                setkey = 'description'
            elif key == 'notes':
                setkey = 'long_description'
            setattr(distutils_metadata, setkey, tval)
        return distutils_metadata

    @classmethod
    def normalize_metadata(self, metadata, keymap=None):
        '''Normalize a metadata dictionary.

        @param keymap: a dictionary that specifies a re-mapping of keys in the input
        metadata to the output metadata dictionary.

        @return: a new normalized dictionary. The dictionary tontains *all* of
        the input key/values but is also 'normalized' in conforming to the
        Metadata.key_list format.

        TODO: do not pass through all key/values from input metadata -- only
        those fitting with the spec.
        '''
        if keymap is None:
            keymap = {}
        newmeta = dict(metadata)
        # complete hack to deal with stringification of data
        if 'extras' in newmeta and newmeta['extras'] == '{}':
            newmeta['extras'] = {}

        if not 'name' in newmeta and 'id' in newmeta:
            newmeta['name'] = newmeta['id']
        if not 'extras' in newmeta:
            newmeta['extras'] = {}
        for inkey,value in metadata.items():
            if inkey in Metadata.key_list:
                continue
            elif inkey in keymap:
                actualkey = keymap[inkey]
                # special case where we append to existing values (as e.g. we
                # may be running together description and comments)
                if actualkey == 'notes':
                    # trim leading '\n' that may result below ...
                    newmeta[actualkey] = newmeta.get(actualkey, '') + os.linesep + value
                elif not actualkey in newmeta:
                    newmeta[actualkey] = value
            else:
                if value is None or value == '':
                    # For extras do not include items where value is 'null'
                    pass
                else:
                    newmeta['extras'][inkey] = value
        # trim leading '\n' that may have resulted from work above
        if 'notes' in newmeta and newmeta['notes'].startswith(os.linesep):
            newmeta['notes'] = newmeta['notes'][len(os.linesep):]
        # TODO extract_extras_from_notes ...

        # normalize tags (from space or comma separated list)
        # ast.literal is there for case where tags = [ 'some thing', 'tag2' ]
        # ast is only in python >= 2.6
        # import ast
        import re
        if 'tags' in newmeta and isinstance(newmeta['tags'], basestring):
            out = newmeta['tags'].strip()
            # still some risk that we have: tags = [weirdtag, ..., otherweirdtag]
            if out.startswith('[') and out.endswith(']'):
                # see comment on ast above
                # newmeta['tags'] = ast.literal_eval(out)
                newmeta['tags'] = re.findall(r'''["']\s*([^"]*?)\s*["']''', out)
            else:
                newmeta['tags'] = re.split('[,\s]+', out)
        if 'download_url' in newmeta:
            # assume resources does not exist
            newmeta['resources'] = [{'url': newmeta['download_url']}]
        return newmeta

    def _extract_extras_from_notes(self):
        pass

