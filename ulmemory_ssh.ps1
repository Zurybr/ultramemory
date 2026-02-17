function ulmemory {
    $config = Get-Content "$env:USERPROFILE\.ulmemory\ssh_config.json" | ConvertFrom-Json
    $server = $config.server_ip
    $user = $config.ssh_user

    # Auto-add "memory" for common commands
    $args = $Args
    $needsMemory = @("add", "query", "count", "analyze", "consolidate", "delete", "research")
    if ($args.Count -gt 0 -and $needsMemory -contains $args[0]) {
        $args = @("memory") + $args
    }

    $cmd = "/home/zurybr/.local/bin/ulmemory " + ($args -join " ")
    ssh -o StrictHostKeyChecking=no "$user@$server" $cmd
}
