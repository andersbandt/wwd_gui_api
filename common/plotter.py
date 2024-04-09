


import matplotlib.pyplot as plt




def time_plot(x_series, y_axis):
    plt.plot(x_series, y_axis)
    plt.grid(True)
    plt.show()



def graph_afe(x_series, afe_d, vertical_lines=None, title=None):
    # f = plt.figure()
    plt.figure(figsize=(12, 6))

    plt.plot(x_series, afe_d)
    # plt.scatter(x_series, afe_d) # this thing honestly sucks for AFE data

    # Add vertical lines
    if vertical_lines is not None:
        for index in vertical_lines:
            plt.axvline(x=index, color='red', linestyle='--', linewidth=2)

    if title is not None:
        plt.title(title)
    else:
        plt.title('AFE ADC data')
    # plt.xlabel('Sample Number')
    plt.xlabel("Time (s)")
    plt.ylabel('ADC Code ?')
    plt.legend(['afe_ADC'])

    plt.tight_layout()


