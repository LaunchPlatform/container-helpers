import typing


def make_mount(params: typing.Dict[str, str]) -> str:
    return ",".join(map(lambda item: "=".join(item), params.items()))


def make_mount_args(params: typing.Dict[str, str]) -> typing.Tuple[str, str]:
    return ("--mount", make_mount(params))


def make_annotation_args(annotations: typing.Dict[str, str]) -> typing.Tuple[str, ...]:
    args = []
    for env_arg in map(lambda item: "=".join(item), annotations.items()):
        args.append("--annotation")
        args.append(env_arg)
    return tuple(args)


def make_env_args(environ: typing.Dict[str, str]) -> typing.Tuple[str, ...]:
    args = []
    for env_arg in map(lambda item: "=".join(item), environ.items()):
        args.append("--env")
        args.append(env_arg)
    return tuple(args)
