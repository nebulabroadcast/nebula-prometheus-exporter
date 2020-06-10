.PHONY: install uninstall


SOURCE=nebula-prometheus-exporter.service
TARGET=/etc/systemd/system/nebula-prometheus-exporter.service

install: $(TARGET)

uninstall:
	rm $(TARGET)

$(TARGET) : $(SOURCE)
	cp $< $@
	sed -i 's+WORKDIR+$(PWD)+g' $@
