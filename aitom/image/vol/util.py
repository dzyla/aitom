import numpy as N
import aitom.image.util as AIU

# convert a 3D cube to a 2D image of slices

def roll(v, s0, s1, s2):
    if (s0 != 0):
        v0 = N.roll(v, s0, axis=0)
    else:
        v0 = v
    if (s1 != 0):
        v1 = N.roll(v0, s1, axis=1)
    else:
        v1 = v0
    if (s2 != 0):
        v2 = N.roll(v1, s2, axis=2)
    else:
        v2 = v1
    return v2


import scipy.ndimage.interpolation as inter

def fft_mid_co(siz):
    assert all((N.mod(siz, 1) == 0))
    assert all((N.array(siz) > 0))
    mid_co = N.zeros(len(siz))
    for i in range(len(mid_co)):
        m = siz[i]
        mid_co[i] = N.floor((m / 2))
    return mid_co


def cub_img(v, view_dir=2):
    if view_dir == 0:
        vt = N.transpose(v, [1, 2, 0])
    elif view_dir == 1:
        vt = N.transpose(v, [2, 0, 1])
    elif view_dir == 2:
        vt = v

    row_num = vt.shape[0] + 1
    col_num = vt.shape[1] + 1
    slide_num = vt.shape[2]
    disp_len = int(N.ceil(N.sqrt(slide_num)))

    slide_count = 0
    im = N.zeros((row_num*disp_len, col_num*disp_len)) + float('nan')
    for i in range(disp_len):
        for j in range(disp_len):
            im[(i*row_num): ((i+1)*row_num-1),  (j*col_num) : ((j+1)*col_num-1)] = vt[:, :, slide_count]
            slide_count += 1

            if (slide_count >= slide_num):
                break

        if (slide_count >= slide_num):
            break

    im_v = im[N.isfinite(im)]

    if im_v.max() > im_v.min():
        im = (im - im_v.min()) / (im_v.max() - im_v.min())

    return {'im': im, 'vt': vt}

# display an image



def dsp_cub(v, view_dir=2, new_figure=True):

    AIU.dsp_img(cub_img(v=v, view_dir=view_dir)['im'])


'''
make a toy structure, and highlight the positive part of Y axis, which is supposed to be tiltling about
also highlight the positive part of x-axis
'''


def highlight_xy_axis(v, dim_siz=64, model_id=0, copy=True):
    if copy:
        v = v.copy()

    c = N.array(v.shape) / 2
    c2 = c / 2

    m = N.abs(v).max()
    v[c[0]:, c[1], c[2]] = m      # highlight positive part of x-axis
    # highlight positive part of x-axis, by adding a short segment in the middle of x axis
    v[c[0]+c2[0], c[1]-c2[1]:c[1]+c2[1], c[2]] = m

    v[c[0], c[1]:, c[2]] = m      # highlight positive part of y-axis

    return v



#-------------------------------------------------------------------
# grid functions

def grid_displacement_to_center(size, mid_co=None):

    size = N.array(size, dtype=N.float)
    assert size.ndim == 1

    if mid_co is None:            mid_co = (N.array(size) - 1) / 2          # IMPORTANT: following python convension, in index starts from 0 to size-1!!! So (siz-1)/2 is real symmetry center of the volume
 
    if size.size == 3:
        # construct a gauss function whose center is at center of volume
        grid = N.mgrid[0:size[0], 0:size[1], 0:size[2]]

        for dim in range(3):
            grid[dim, :, :, :] -= mid_co[dim]

    elif size.size == 2:
        # construct a gauss function whose center is at center of volume
        grid = N.mgrid[0:size[0], 0:size[1]]

        for dim in range(2):
            grid[dim, :, :] -= mid_co[dim]

    else:
        assert False

    return grid

def grid_distance_sq_to_center(grid):
    dist_sq = N.zeros(grid.shape[1:])
    if grid.ndim == 4:
        for dim in range(3):
            dist_sq += N.squeeze(grid[dim, :, :, :]) ** 2
    elif grid.ndim == 3:
        for dim in range(2):
            dist_sq += N.squeeze(grid[dim, :, :]) ** 2
    else:
        assert False

    return dist_sq

def grid_distance_to_center(grid):
    dist_sq = grid_distance_sq_to_center(grid)
    return N.sqrt(dist_sq)


# -----------------------------------------------------------------------------------

# roughly add a small vol to a big whole map, so that the center of vol is roughly centered at c
def add_to_whole_map(whole_map, vol, c=None):

    if c is None:
        c = N.array(whole_map.shape) / 2

    c = N.round(c)

    siz = N.array(vol.shape)

    se = subvolume_center_start_end(
        c, map_siz=N.array(whole_map.shape), subvol_siz=siz)
    if se is None:
        return None

    # we also handle NaN in the whole map, and replace them with valid values in local map (if any)
    local_map = whole_map[se[0, 0]:se[0, 1],
                          se[1, 0]:se[1, 1], se[2, 0]:se[2, 1]]
    local_map[N.isnan(local_map)] = 0
    local_map += vol

    whole_map[se[0, 0]:se[0, 1], se[1, 0]              :se[1, 1], se[2, 0]:se[2, 1]] = local_map

    return whole_map


# roughly paste a small vol to a big whole map, so that the center of vol is roughly centered at c
def paste_to_whole_map(whole_map, vol, c=None):

    if c is None:
        c = N.array(whole_map.shape) / 2

    c = N.round(c)

    siz = N.array(vol.shape)

    se = subvolume_center_start_end(c, map_siz=whole_map.shape, subvol_siz=siz)
    if se is None:
        return None

    paste_to_whole_map__se(whole_map, vol, se)

    return whole_map


# paste to a map given start and end coordinates
def paste_to_whole_map__se(whole_map, vol, se):
    whole_map[se[0, 0]:se[0, 1], se[1, 0]:se[1, 1], se[2, 0]:se[2, 1]] = vol


def cut_from_whole_map(whole_map, c, siz):

    se = subvolume_center_start_end(c, map_siz=whole_map.shape, subvol_siz=siz)
    return cut_from_whole_map__se(whole_map, se)


# cut a map given start and end coordinates
def cut_from_whole_map__se(whole_map, se):
    if se is None:
        return None
    return whole_map[se[0, 0]:se[0, 1], se[1, 0]:se[1, 1], se[2, 0]:se[2, 1]]


# given a center c, get the relative start and end position of a subvolume with size subvol_siz
def subvolume_center_start_end(c, map_siz, subvol_siz):
    map_siz = N.array(map_siz)
    subvol_siz = N.array(subvol_siz)

    siz_h = N.ceil(subvol_siz / 2.0)

    start = c - siz_h
    start.astype(int)
    end = start + subvol_siz
    end.astype(int)

    if any(start < 0):
        return None
    if any(end >= map_siz):
        return None

    se = N.zeros((3, 2), dtype=N.int)
    se[:, 0] = start
    se[:, 1] = end

    return se
