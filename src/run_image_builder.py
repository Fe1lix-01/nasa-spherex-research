import warnings

from spexpi.image_builder import create_images

warnings.filterwarnings("ignore")

# ------------------------------------------------------
# Spectral standards
# ------------------------------------------------------

ra, dec = 265.349, 25.882
object_name = "T9 WISEP J174124.25+255319.5"

ra, dec = 63.849, -9.582
object_name = "T8 2MASSI J0415195-093506"

ra, dec = 111.835, 17.161
object_name = "T7 2MASSI J0727182+171001"

ra, dec = 226.6945, 70.4635
object_name = "T6 2MASS J15065257+7027247"

ra, dec = 225.833, 25.425
object_name = "T5 2MASS J15031961+2525196"

ra, dec = 343.580, 31.398
object_name = "T4 2MASSI J2254188+312349"

ra, dec = 104.043, 42.092
object_name = "T3 2MASS J06560926+4205301"

ra, dec = 193.722, -1.380
object_name = "T2 SDSSp J125453.90-012247.4"

ra, dec = 191.624, -31.663
object_name = "T1 2MASS J12462965-3139280"

ra, dec = 181.944, 2.740
object_name = "T0 SDSS J120747.17+024424.8"

ra, dec = 43.777, -47.019
object_name = "L9 DENIS-P J0255-4700"

ra, dec = 248.125, 19.077
object_name = "L8 2MASSW J1632291+190441"

ra, dec = 327.076, 40.069
object_name = "L7 2MASSW J2148162+400359"

ra, dec = 152.560, -4.115
object_name = "L6 2MASSI J1010148-040649"

ra, dec = 128.776, 19.883
object_name = "L5 SDSS J083506.16+195304.4"

ra, dec = 329.520, -15.837
object_name = "L4 2MASS J21580457-1550098"

ra, dec = 226.719, 13.351
object_name = "L3 2MASSW J1506544+132106"

ra, dec = 196.416, -25.686
object_name = "L2 Kelu-1"

ra, dec = 219.859, 19.490
object_name = "L1 2MASSW J1439284+192915"

ra, dec = 56.430, 25.672
object_name = "L0 2MASP J0345432+254023"

ra, dec = 217.178, 33.172
object_name = "M9 LHS 2924"

ra, dec = 289.236, 5.140
object_name = "M8 VB 10"

ra, dec = 253.892, -8.401
object_name = "M7 VB 8"

cutout_size_arcsec = 100
data_dir = "../resources/standards/data/" + object_name.replace(" ", "_")
output_dir = "../resources/standards/images"

create_images(ra, dec, data_dir, output_dir, object_name, cutout_size_arcsec, open_plot=True)
