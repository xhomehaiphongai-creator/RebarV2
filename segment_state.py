# -*- coding: utf-8 -*-

def make_segment_key(info):
    try:
        return str(info["id"])
    except:
        try:
            return str(info["element"].Id)
        except:
            return str(id(info))


def default_settings():
    return {
        "cx_count": 2,
        "cy_count": 2,
        "main_bar": u"",
        "tie_bar": u"D6",
        "hook_bar": u"D6",
        "layout": u"L1, L2, L1",
        "top_cover_mm": u"25",
        "section_ties": []
    }


class SegmentStateStore(object):
    def __init__(self):
        self._data = {}

    def ensure(self, info, fallback=None):
        key = make_segment_key(info)
        if key not in self._data:
            data = default_settings()
            if fallback:
                for k, v in fallback.items():
                    data[k] = v
            self._data[key] = data
        return self._data[key]

    def get(self, info):
        key = make_segment_key(info)
        return self._data.get(key, None)

    def set(self, info, settings_dict):
        key = make_segment_key(info)
        self._data[key] = dict(settings_dict)

    def clone_from_source_to_targets(self, source_info, target_infos):
        src = self.get(source_info)
        if src is None:
            src = self.ensure(source_info)

        for info in target_infos:
            copied = dict(src)
            copied["section_ties"] = [dict(x) for x in src.get("section_ties", [])]
            self.set(info, copied)