pestchek opt |& tee 0_pest_check_results
inschek observations.dat.ins observations.dat |& tee -a 0_pest_check_results
tempchek parameters.dat.tpl parameters.dat.tpl.tempcheck.dat trial.par |& tee -a /home/matt_dumont/unbacked/hawea/terrace_only/init_terrace_only/Optimisations/0_pest_check_results
