opt=/home/matt_dumont/PycharmProjects/hawea_model_optimisation_NO_EDIT
mtools=/home/matt_dumont/PycharmProjects/modflow_tools_haw_NO_EDIT

mkdir $opt
git clone git@github.com:Komanawa-Solutions-Ltd/Z22031HAW_hawea-model $opt
cd $opt
git fetch --all
git reset --hard origin/structure_v9

mkdir $mtools
git clone git@github.com:Komanawa-Solutions-Ltd/modflow_tools $mtools
cd $mtools
git fetch --all
git reset --hard origin/Z22031HAW_hawea-model