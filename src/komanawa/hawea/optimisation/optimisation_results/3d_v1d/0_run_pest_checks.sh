pestchek opt |& tee 0_pest_check_results
inschek observations.dat.ins observations.dat |& tee -a 0_pest_check_results
tempchek parameters.dat.tpl parameters.dat.tpl.tempcheck.dat trial.par |& tee -a /home/matt_dumont/unbacked/hawea/3d_v1d/init_3d_v1d/Optimisations/0_pest_check_results
