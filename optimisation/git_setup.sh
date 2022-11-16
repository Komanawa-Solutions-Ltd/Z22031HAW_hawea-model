opt=/home/matt_dumont/PycharmProjects/hawea_model_optimisation_NO_EDIT
mtools=/home/matt_dumont/PycharmProjects/modflow_tools_haw_NO_EDIT

mkdir $opt
cd $opt
git clone git@github.com:Komanawa-Solutions-Ltd/Z22031HAW_hawea-model
git fetch --all
git reset --hard origin/structure_v9

mkdir $mtools
cd $mtools
git clone git@github.com:Komanawa-Solutions-Ltd/modflow_tools
git fetch --all
git reset --hard origin/Z22031HAW_hawea-model