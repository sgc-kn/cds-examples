{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.cdo

    # keep this line if you use bash
    pkgs.bashInteractive
  ];
}
