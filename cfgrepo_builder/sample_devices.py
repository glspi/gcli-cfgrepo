username = "admin"
password = "admin"

devices = {
    "spine1": (
        #"172.254.0.11", 22
        "10.254.254.59", 21022
    ),
    "spine2": (
        #"172.254.0.12", 22
        "10.254.254.59", 22022
    )
    # "leaf1": (
    #     "172.254.0.21",
    #     22 if DOCKER else 2221,
    # ),
    # "leaf2": (
    #     "172.254.0.22",
    #     22 if DOCKER else 2222,
    # ),
}