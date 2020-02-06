
def deformalize(form):
    result = {}
    for k in form:
        ordinal = k.split("_")[-1]
        if not ordinal in result.keys():
            result[ordinal] = {}
        result[ordinal]["_".join(k.split("_")[0:-1])] = form[k]
    return list(result.values())

def time_ago(seconds):
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if s < 1:s = 0
    locals_ = locals()
    magnitudes_str = ("{n}{magnitude}".format(n=int(locals_[magnitude]), magnitude=magnitude) for magnitude in ("d", "h", "m", "s") if locals_[magnitude])
    result = " ".join(magnitudes_str) if s >= 1 else "N/A"
    return result

