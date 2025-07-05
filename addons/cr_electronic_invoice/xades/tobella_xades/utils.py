
# © 2017 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def dict_compare(dict1, dict2):
    assert len(dict1) == len(dict2)
    dict1_keys = set(dict1.keys())
    dict2_keys = set(dict2.keys())
    intersect_keys = dict1_keys.intersection(dict2_keys)
    assert len(intersect_keys) == len(dict1)
    for key in dict1_keys:
        assert dict1[key] == dict2[key]


def rdns_to_map(data):
    return {x.split('=')[0].strip(): x.split('=')[1].strip() for x in data.split(',') if x}
