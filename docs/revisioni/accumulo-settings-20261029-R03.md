# Allineamento impostazioni tipizzate accumulo, R03

29/10/2026. Diagnosi dal log `build/services-final-nucleo-R01.log`: test `Mirror.test_the_losses_the_consumption_and_the_economics_match_the_energy_side` fallito perché `settings.EconomicsSettings` non conteneva `storage_coupling`, `storage_inverter`, `storage_efficiency_pct`, presenti nel modello di calcolo.

[V] Riprodotto lo stesso errore con il gruppo mirato `test_settings.py`. Aggiunta regressione che dimostra la perdita dei tre campi nella lettura tipizzata (prima riconosciuti come sconosciuti), l'accettazione del rendimento nullo e numerico e il rifiuto di un booleano.

[V] Correzione: aggiunti i tre campi e i default speculari a `energy.economics.Settings`. Non modificata la migrazione del progetto: i campi restano nel dizionario economics già compatibile. Ora il controllo tipi e la lista dei percorsi riconosciuti li includono.

[V] Passati 7 test settings, 14 test storage e Ruff sui due file modificati. Non rilanciata la suite completa e non avviato il build Flatpak in attesa del nuovo freeze.
