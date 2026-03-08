# speech-to-text

## Popis

Program pro konverzi mluveného slova na text. 

Program čeká na dvojí stisknutí klávesy Ctrl a poté nahraje vstup z mikrofonu (ukončeno dvojím stisknutím klávesy Ctrl), odešle na rozpoznávání mluvené řeči a na místo kurzoru do libovolné aplikace vloží rozpoznaný text. Během nahrávání se pauznou přehrávače hudby.

## Spuštění

Je potřeba nainstalovat závislosti a potom spustit následující příkaz. Předpokládá se, že v souboru `api.txt` je přislušný api klíč.

```
export GROQ_API_KEY=`cat api.txt`; python voice_to_text.py
```

## Related stuff

* https://jan.fertek.cz/2025/speech-to-text-aneb-jak-na-linuxu-diktovat-do-libovolne-aplikace/#postup-instalace
* https://www.reddit.com/r/LocalLLaMA/comments/1nc7bxw/fast_local_pushtotalk_speechtotext_dictation_tool/?tl=cs
* https://github.com/lxe/yapyap
* https://github.com/openconcerto/MisterWhisper
* https://gist.github.com/victorb/5ab57b42f8f75fccefb213bafbe69d10
* https://github.com/ideasman42/nerd-dictation
* https://github.com/papoteur-mga/elograf
* https://github.com/diogovalada/whisper-writer
* https://vocalinux.com/
