#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
# See LICENSE file for licensing details.
"""Operator charm main library."""
import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main

from lib_cloudsupport import CloudSupportHelper
from os_testing import create_instance, delete_instance, test_connectivity


class CloudSupportCharm(CharmBase):
    """Operator charm class."""

    state = StoredState()

    def __init__(self, *args):
        """Initialize charm and configure states and events to observe."""
        super().__init__(*args)
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(
            self.on.create_test_instance_action, self.on_create_test_instance
        )
        self.framework.observe(
            self.on.delete_test_instance_action, self.on_delete_test_instance
        )
        self.framework.observe(
            self.on.test_connectivity_action, self.on_test_connectivity
        )
        self.state.set_default(installed=False)
        self.helper = CloudSupportHelper(self.model)

    def on_install(self, event):
        """Install charm and perform initial configuration."""
        self.helper.update_config()
        self.state.installed = True

    def on_config_changed(self, event):
        """Reconfigure charm."""
        if not self.state.installed:
            logging.info(
                "Config changed called before install complete, deferring event: "
                "{}".format(event.handle)
            )
            event.defer()
            return
        self.helper.update_config()

    def on_create_test_instance(self, event):
        """Run create-test-instance action."""
        cfg = self.model.config
        nodes = event.params["nodes"].split(",")
        physnet = event.params.get("physnet")
        vcpus = event.params.get("vcpus", cfg["vcpus"])
        vnfspecs = event.params.get("vnfspecs")
        try:
            create_results = create_instance(
                nodes,
                vcpus,
                cfg["image"],
                cfg["name-prefix"],
                cfg["cidr"],
                physnet=physnet,
                vnfspecs=vnfspecs,
            )
        except BaseException as err:
            event.set_results({"error": err})
            raise
        errs = any([a for a in create_results if a[0] == "error"])
        event.set_results(
            {
                "create-results": "success" if not errs else "error",
                "create-details": create_results,
            }
        )

    def on_delete_test_instance(self, event):
        """Run delete-test-instance action."""
        nodes = event.params["nodes"].split(",")
        pattern = event.params["pattern"]
        delete_results = delete_instance(nodes, pattern)
        event.set_results({"delete-results": delete_results})

    def on_test_connectivity(self, event):
        """Run test-connectivity action."""
        try:
            test_results = test_connectivity(event.params.get("instance"))
        except BaseException as err:
            event.set_results({"error": err})
            raise
        event.set_results(test_results)


if __name__ == "__main__":
    main(CloudSupportCharm)
