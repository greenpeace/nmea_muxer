
def deformalize(form):
    result = {}
    for k in form:
        ordinal = k.split("_")[-1]
        if not ordinal in result.keys():
            result[ordinal] = {}
        result[ordinal]["_".join(k.split("_")[0:-1])] = form[k]
    return list(result.values())

def time_ago(seconds):
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if seconds < 1:seconds = 1
    locals_ = locals()
    magnitudes_str = ("{n} {magnitude}".format(n=int(locals_[magnitude]), magnitude=magnitude) for magnitude in ("days", "hours", "minutes", "seconds") if locals_[magnitude])
    return ", ".join(magnitudes_str)
