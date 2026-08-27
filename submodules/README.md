# Repository Submodules

To update all submodules:

```sh
git pull --recurse-submodules
git submodule update --remote --recursive
```

If you did not clone with `--recursive` and ended up with empty submodule
directories, you can fetch them with:

```sh
git submodule update --init --recursive
```
