from numpy import exp, abs, round
from sys import stdout

def FtoC(F):
    '''
    This function simply converts Fahrenheit temepratures to Celcius
    '''
    return (F - 32) * 5. / 9.

def CtoF(C):
    '''
    This function simply converts Celcius temepratures to Fahrenheit
    '''
    return (9. / 5. * C) + 32

def SWVP_func(C):
    '''
    This function computes the Saturated Water Vapor Pressure
    of air at a given Dry Buld Temeprature in Celcius.

    The equation normally produces a result in millibars, but the 0.0295 
    converts it to inHg.
    '''
    return (6.108 * .0295333727 * (exp((17.27 * C) / (273.3 + C))))

def unsolved(x, y, accuracy):
    '''
    This is the conditional test for the numpy array fed to it.  It produces a vector of 
    booleans, and then those can be used for the calculation.
    '''
    #accuracy = 0.001
    us = abs((x-y)/x) > accuracy
    #this is the try to make a good progress bar for this.
    error_amount = abs((x-y)/x).sum().astype(float)

    return us, error_amount

def WBT_and_Enthalpy(F, H, P, accuracy):
    '''
        this function takes in the dry bulb temperature in farhenheit, the relative
        humidity in '%', and the atmospheric pressure in inHg,
        and returns the WBT in farhenheit and the enthalpy in BTU/lb
    '''
    SWVP = SWVP_func(FtoC(F))
    AWVP = SWVP * H / 100.
    w = 0.622 * (AWVP) / (P - AWVP) 
    Enthalpy = (0.24 * F) + w * (0.45 * F + 1061)

    us, orig_err = unsolved(AWVP, SWVP, accuracy)
    #make the first guess right below the DBT
    G = F.copy()

    while us.any():
        G[us] = G[us] - accuracy
        SWVP_G = SWVP_func(FtoC(G))
        AWVP_G = SWVP_G - ((P - SWVP_G) * (F - G) / (2800. - 1.3 * G))
        us, cur_err = unsolved(AWVP, AWVP_G, accuracy)
        percent = ((orig_err - cur_err)/orig_err)*100.
        stdout.write('\rCalculating WBT: %f percent' %(round(percent, 2)))
        stdout.flush()

    print '\n\nDone!\n'
    return (round(G, 1), round(Enthalpy, 1))
