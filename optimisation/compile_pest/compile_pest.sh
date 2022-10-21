# note that I have changed the max character limits in pest following 2.7 in unixpest.pdf
# new limits were set to 300 characters, max characters is 77 in a single line
# pest was run on ubuntu (xubuntu) 22.04

# install GFORTRAN if  needed
sudo apt-get update
sudo apt-get install gfortran
sudo apt-get install make

pest_dir='/pest'
base_tar="./pest17_mod.tar"

sudo mkdir $pest_dir

#  copy tar to directory to use
sudo cp $base_tar "$pest_dir/pest17_mod.tar"

# move to working directory
cd "$pest_dir/pest_source"

# extract
sudo tar -xvf pest17_mod.tar

# compile PEST
sudo make cppp
sudo make -f pest.mak all
sudo make clean
sudo make -f ppest.mak all
sudo make clean
sudo make -f pestutl1.mak all
sudo make clean
sudo make -f pestutl2.mak all
sudo make clean
sudo make -f pestutl3.mak all
sudo make clean
sudo make -f pestutl4.mak all
sudo make clean
sudo make -f pestutl5.mak all
sudo make clean
sudo make -f pestutl6.mak all
sudo make clean
sudo make -f pestutl7.mak all
sudo make clean
sudo make -f sensan.mak all
sudo make clean
sudo make -f beopest.mak all
sudo make clean
sudo mkdir /bin/pest
sudo make install

# add pest path variable
echo 'export PATH="$PATH:/bin/pest"' >> ~/.bashrc
source ~/.bashrc

# delete pest dir
sudo rm -r $pest_dir
