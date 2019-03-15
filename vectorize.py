#https://github.com/SpaceNetChallenge/RoadDetector/blob/master/pfr-solution/code/rd.py

from scipy.spatial import cKDTree
from shapely.ops import linemerge

def vectorize_skeleton(img, stride, tolerance, preserve_topology=True, remove_hair=0):
    # Extract the image's graph.
    i,j = np.nonzero(img)
    unscaled_xy = np.c_[j,i]
    xy = unscaled_xy * stride * (len(img) / (len(img) - 1)) # minor expansion to ensure exact fit to borders
    xy = xy.round(2)
    try:
        u,v = np.array(list(cKDTree(xy).query_pairs(1.5*stride))).T
    except ValueError:
        return linemerge([])

    # Make sure that no triangles will form at T junctions.
    unscaled_xy_set = set(map(tuple, unscaled_xy))
    unscaled_xy_u = unscaled_xy[u]
    unscaled_xy_v = unscaled_xy[v]
    is_diagonal = np.sum((unscaled_xy_v - unscaled_xy_u)**2, axis=-1) == 2
    keep_mask = ~is_diagonal.copy()
    for k in np.flatnonzero(is_diagonal):
        a = unscaled_xy_u[k]
        b = unscaled_xy_v[k]
        c = (a[0], b[1])
        d = (b[0], a[1])
        if c in unscaled_xy_set or d in unscaled_xy_set:
            keep_mask[k] = False
        else:
            keep_mask[k] = True
    u = u[keep_mask]
    v = v[keep_mask]

    # Convert to Shapely shape.
    lines = np.array([xy[u], xy[v]]).swapaxes(0,1)
    shape = linemerge(lines).simplify(tolerance, preserve_topology=preserve_topology)

    # Remove any short deadends created by skeletonization.
    if remove_hair:
        strings = list(as_MultiLineString(shape))
        arity = {}
        for strn in strings:
            for point in strn.coords:
                arity.setdefault(point, 0)
                arity[point] += 1

        good_strings = []
        for strn in strings:
            if (arity[strn.coords[0]] != 1 and arity[strn.coords[-1]] != 1) \
               or strn.length >= remove_hair:
                good_strings.append(strn)
        shape = MultiLineString(good_strings)
        

    return shape

