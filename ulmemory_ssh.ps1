function ulmemory {
    $config = Get-Content "$env:USERPROFILE\.ulmemory\ssh_config.json" | ConvertFrom-Json
    $server = $config.server_ip
    $user = $config.ssh_user
    $cmd = "ulmemory " + ($Args -join " ")
    ssh -o StrictHostKeyChecking=no "$user@$server" $cmd
}
