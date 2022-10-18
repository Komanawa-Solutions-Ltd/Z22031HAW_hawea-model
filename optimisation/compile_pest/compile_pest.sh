# note that I have changed the max character limits in pest following 2.7 in unixpest.pdf
# new limits were set to 300 characters, max characters is 77 in a single line

# install GFORTRAN if  needed # todo

pest_dir='/pest'
base_tar=dirname -- "$( readlink -f -- "$0"; )"; # todo get access to the path


mkdir $pest_dir
# todo copy tar to directory to use
cp

#

# todo move to working directory
cd $pest_dir

# extract
tar – xvf pest17_mod.tar # todo check line
# todo 2.2 Symbols used with Compiler Directives, I don't understand

# compile PEST
make cppp
make -f pest.mak all
make clean
make -f ppest.mak all
make clean
make -f pestutl1.mak all
make clean
make -f pestutl2.mak all
make clean
make -f pestutl3.mak all
make clean
make -f pestutl4.mak all
make clean
make -f pestutl5.mak all
make clean
make -f pestutl6.mak all
make clean
make -f pestutl7.mak all
make clean
make -f sensan.mak all
make clean
4make –f beopest.mak all
make clean
make install