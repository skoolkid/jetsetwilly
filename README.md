Jet Set Willy disassembly
=========================

A disassembly of the [Spectrum](https://en.wikipedia.org/wiki/ZX_Spectrum)
version of [Jet Set Willy](https://en.wikipedia.org/wiki/Jet_Set_Willy),
created using [SkoolKit](https://skoolkit.ca/).

Decide which number base you prefer and then click the corresponding link below
to browse the latest release:

* [Jet Set Willy disassembly](https://skoolkid.github.io/jetsetwilly/) (hexadecimal; mirror [here](https://skoolkid.gitlab.io/jetsetwilly/))
* [Jet Set Willy disassembly](https://skoolkid.github.io/jetsetwilly/dec/) (decimal; mirror [here](https://skoolkid.gitlab.io/jetsetwilly/dec/))

To build the current development version of the disassembly, first obtain the
development version of [SkoolKit](https://github.com/skoolkid/skoolkit). Then:

    $ skool2html.py sources/jsw.skool

To build an assembly language source file that can be fed to an assembler:

    $ skool2asm.py sources/jsw.skool > jsw.asm
