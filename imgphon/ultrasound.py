import numpy as np
from scipy.ndimage import median_filter
from scipy.ndimage.filters import gaussian_laplace

def normalize(frame):
    ''' Normalize input image to range [0,1]. TODO more descriptive name? '''
    mx = float(np.amax(frame))
    mn = float(np.amin(frame))
    norm = (frame-mn)/(mx-mn)

    return norm

def srad(frame, n_iter=300, lbda=0.05):
    '''
    Speckle-reducing anisotropic diffusion filter to reduce noise
      typical of ultrasound images. Derived from MATLAB code in  
      Chris Carignan's TRACTUS repo 
      (https://github.com/ChristopherCarignan/TRACTUS/, in SRAD.m)
      which is in turn derived from the original algorithm in 
      Yu, Y. & Acton, S. (2002), "Speckle Reducing Anisotropic 
      Diffusion", IEEE Transactions on Image Processing 11(11), 
      DOI 10.1109/TIP.2002.804276.

    Inputs: frame, an ultrasound frame
      n_iter: number of iterations (Y&A use 300)
      lbda: lambda, AKA delta-t in Y&A (who use 0.05)
    Outputs: J, filtered ultrasound frame.
    '''

    # checks on I for number/type
    # TODO

    # scale to [0,1]
    I = normalize(frame)

    # get image size
    M,N = I.shape

    # image indices, using boundary conditions 
    iN = np.concatenate((np.arange(0, 1), np.arange(0, M-1)), axis=0)
    iS = np.concatenate((np.arange(1, M), np.arange(M-1, M)), axis=0) 
    jW = np.concatenate((np.arange(0, 1), np.arange(0, N-1)), axis=0)
    jE = np.concatenate((np.arange(1, N), np.arange(N-1, N)), axis=0)

    # log uncompress
    I = np.exp(I)

    # the algorithm itself
    for n in range(0,n_iter):

        # speckle scale fcn
        # IC = I.copy()
        # Iuniform = IC.crop(rect)
        q0_squared = np.var(I) / (np.mean(I)**2)

        # differences, element-by-element along each row moving from given direction (N, S, E, W)
        dN = I[iN,:] - I
        dS = I[iS,:] - I
        dW = I[:,jW] - I
        dE = I[:,jE] - I

        # normalized discrete gradient magnitude squared (Yu and Acton eqn. 52, 53)
        G2 = (dN**2 + dS**2 + dW**2 + dE**2) / I**2

        # normalized discrete Laplacian (eqn. 54)
        L = (dN + dS + dW + dE) / I

        # instantaneous coefficient of variation (ICOV) (eqns. 31/35)
        num = (.5*G2) - ((1/16)*(L**2))
        den = (1. + ((.25)*L))**2
        q_squared = num / (den + np.spacing(1))

        # diffusion coefficient (eqn. 33) # TODO why is this also "den"?
        den = (q_squared - q0_squared) / (q0_squared * (q0_squared + 1) + np.spacing(1))
        c = 1 / (den + 1)

        # saturate diffusion coefficient 
        c[np.where(c<0)] = 0 # negative = FALSE
        c[np.where(c>0)] = 1 # positive = TRUE

        # divergence (eqn. 58)
        cS = c[iS,:] 
        cE = c[:,jE] 
        D = (c * dN) + (cS * dS) + (c * dW) + (cE * dE)

        # SRAD update fcn (eqn. 61)
        I = I + (lbda/4) * D

    # log (re)compress
    J = np.log(I) 

    return J

def clean_frame(frame, median_radius=10, log_sigma=6):
    """
    Cleanup function to be run on SRAD output. Median filter for
      further denoising, followed by edge sharpening with a Laplacian 
      of Gaussian (LoG) mask.

    Inputs: ndarray image, filter kernel settings
      median_radius: median filter radius; should be odd integer
      log_sigma: LoG sigma; controls kernel size
    Output: cleaned; a processed ndarray
      
    """

    # TODO provide default for median_radius that is 
    #   sensitive to image dimensions

    medfilt = median_filter(frame, median_radius)
    logmask = gaussian_laplace(medfilt, log_sigma)
    cleaned = medfilt + logmask

    # TODO prevent "overflows" that arise from running on non-float data
    
    return cleaned

def roi_select(frame, lower, upper):
    """
    Defines region of interest along ultrasound scan lines; returns 
      frame with content outside of this region removed. RoI is 
      rectangular in raw data, and thus bounded by two arcs in scan- 
      converted data.

    Inputs: 
      frame: ultrasound data in ndarray
      lower: bound of RoI closer to probe
      upper: bound of RoI further away from probe

    Outputs: 
      region: frame containing data only in region of interest

    TODO add bgcolor parameter
    """
    if lower >= upper:
        raise ValueError("ROI lower bound must be below upper bound")
    region = np.zeros(td.shape, dtype=td.dtype)
    region[lower:upper,:] = td[lower:upper,:]
    
    return region

"""
RoI pseudocode (frame, manual=False, convert=False):

    for each unconverted frame in an experiment:
        grab the frame and put it in an array
        
    flatten the array to produce a heatmap

    if manual:
        bring up the heatmap in a window and let the user select the RoI as a slice of rows
    else:
        automatically generate the RoI using image processing stuff

    generate a RoI mask based on selected RoI

    if convert:
        RoI mask gets converted into fan shape

    return RoI
"""

# TODO: group frames into training/test from a PD DataFrame

# TODO: PCA on arrays in short dimension (ideally, on frame bundles) - linked DataFrame?

# TODO: LDA on arrays - but what kind of object? DataFrame?