{
  description = "NeoTime: a wasp-os fork for the PineTime";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # nixpkgs marks ecdsa insecure, and the DFU packaging step needs it.
        pkgs = import nixpkgs {
          inherit system;
          config.permittedInsecurePackages = [ "python3.13-ecdsa-0.19.1" ];
        };

        # Everything the simulator, the tests and the packaging tools import.
        python = pkgs.python3.withPackages (ps: with ps; [
          click
          cryptography
          intelhex
          numpy
          pexpect
          pillow
          pyserial
          pysdl2
          pytest
          tomli
        ]);

        # The firmware is built with the ARM cross compiler, not the host one.
        arm = pkgs.gcc-arm-embedded-13;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            arm
            pkgs.SDL2
            pkgs.bluez
            pkgs.git
            pkgs.gnumake
            pkgs.unzip
            pkgs.wget
          ];

          # pysdl2 loads SDL2 at runtime and will not find it otherwise.
          PYSDL2_DLL_PATH = "${pkgs.SDL2}/lib";

          # The Makefile shells out to python for mpy-cross, the DFU package
          # and the app tools, so point it at the one with the dependencies.
          PYTHON = "${python}/bin/python3";

          shellHook = ''
            echo "NeoTime"
            echo "  make BOARD=pinetime all   build bootloader, reloader and firmware"
            echo "  make sim                  run the simulator"
            echo "  make check                run the simulator test suite"
            echo "  pytest tools/             run the packaging tool tests"
            echo
            echo "python  $(python3 --version)"
            echo "arm-gcc $(arm-none-eabi-gcc -dumpversion)"
            echo
            echo "A headless simulator run also needs SDL_VIDEODRIVER=dummy."
          '';
        };
      });
}
