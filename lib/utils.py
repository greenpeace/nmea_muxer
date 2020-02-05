
def deformalize(form):
    result = {}
    for k in form:
        ordinal = k.split("_")[-1]
        if not ordinal in result.keys():
            result[ordinal] = {}
        result[ordinal]["_".join(k.split("_")[0:-1])] = form[k]
    return list(result.values())
