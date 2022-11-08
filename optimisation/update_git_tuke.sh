# setup
# mkdir "~/PycharmProjects/modflow_tools_haw"
# mkdir "~/PycharmProjects/Z22031HAW_hawea-model"
# git clone git@github.com:Komanawa-Solutions-Ltd/modflow_tools  ~/PycharmProjects/modflow_tools_haw
# git clone git@github.com:Komanawa-Solutions-Ltd/Z22031HAW_hawea-model  ~/PycharmProjects/Z22031HAW_hawea-model

cd ~/PycharmProjects/modflow_tools_haw
git fetch --all
git reset --hard origin/Z22031HAW_hawea-model

cd ~/PycharmProjects/Z22031HAW_hawea-model
git fetch --all
git reset --hard origin/structure_v4  # todo up date this
