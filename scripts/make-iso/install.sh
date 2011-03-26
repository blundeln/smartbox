# Get sbinstaller
wget http://www.nickblundell.org.uk/packages/sbinstaller
mv sbinstaller /usr/bin/
chmod +x /usr/bin/sbinstaller

# Remove from startup now.
sed -i 's_sh /root/install.sh_exit 0_' /etc/rc.local

echo "Smartbox installation complete."
